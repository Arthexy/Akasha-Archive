from types import SimpleNamespace
from unittest.mock import AsyncMock

import genshin
import pytest

from config import HoyoSettings
from enka_client import allowed_image
from errors import HubError
from exploration import normalize_exploration
from hoyolab_client import HoYoLABClient


def entry(id, name, progress=None, **extra):
    return dict(id=id, name=name, parent_id=0, world_type=2, exploration_percentage=progress, **extra)


def test_special_maps_and_children_count_once():
    raw = [entry(2, 'Liyue', 500),
           entry(10, 'Chenyu Vale', 0),
           entry(11, 'Upper Vale', 200), entry(12, 'Southern Vale', 600)]
    raw[1]['world_type'] = 1
    raw[2]['parent_id'] = raw[3]['parent_id'] = 10
    result = normalize_exploration(raw)
    assert len(result['regions']) == 2
    assert result['regions'][1]['progress'] == 40
    assert result['regions'][1]['group_id'] == '10'
    assert result['groups'] == [{'id': '2', 'name': 'Liyue', 'progress': 50}, {'id': '10', 'name': 'Chenyu Vale', 'progress': 40}]


def test_frost_moon_is_displayed_separately_without_double_counting():
    result = normalize_exploration([entry(17, 'Nod-Krai', 800, area_exploration_list=[
        {'name': 'Paha Isle', 'exploration_percentage': 1050},
        {'name': 'Dark Side of the Moon', 'exploration_percentage': 300}])])
    assert result['groups'][0]['progress'] == 80
    assert result['regions'][0]['areas'][0]['progress'] == 100
    moon = result['regions'][1]
    assert moon['name'] == 'Frost Moon' and moon['progress'] == 30
    assert moon['included_in_main'] is True


def test_chenyu_and_chasm_have_independent_selection_groups():
    result = normalize_exploration([entry(2, 'Liyue', 500), entry(6, 'The Chasm', 800), entry(10, 'Chenyu Vale', 400)])
    chasm = next(r for r in result['regions'] if r['name'] == 'The Chasm')
    chenyu = next(r for r in result['regions'] if r['name'] == 'Chenyu Vale')
    assert chasm['group_id'] == '6' and chenyu['group_id'] == '10'
    assert chasm['group_name'] == chenyu['group_name'] == 'Liyue'
    assert chasm['special'] and chenyu['special']
    assert {g['id']: g['progress'] for g in result['groups']} == {'2': 50, '6': 80, '10': 40}


def test_chasm_surface_and_underground_progress_are_preserved():
    raw = [entry(2, 'Liyue', 1000), entry(6, 'The Chasm', 398),
           entry(7, 'The Chasm: Underground Mines', 1000)]
    raw[1]['world_type'] = raw[2]['world_type'] = 1
    raw[2]['parent_id'] = 6
    result = normalize_exploration(raw)
    chasm = result['regions'][1]
    assert [a['progress'] for a in chasm['areas']] == [39.8, 100]
    assert chasm['progress'] == 69.9
    assert result['groups'] == [{'id': '2', 'name': 'Liyue', 'progress': 100}, {'id': '6', 'name': 'The Chasm', 'progress': 69.9}]


def test_moon_areas_move_together_and_windrest_belongs_to_mondstadt():
    result = normalize_exploration([
        entry(1, 'Mondstadt', 800), entry(21, 'Windrest Peak', 600),
        entry(17, 'Nod-Krai', 900, area_exploration_list=[
            {'name': name, 'exploration_percentage': progress}
            for name, progress in [('Paha Isle', 700), ('Lunar Island', 200), ('Moontide Isle', 400)]])])
    moon = next(r for r in result['regions'] if r['name'] == 'Frost Moon')
    mondstadt = next(r for r in result['regions'] if r['name'] == 'Mondstadt')
    assert [a['name'] for a in moon['areas']] == ['Lunar Island', 'Moontide Isle']
    assert moon['progress'] == 30 and moon['included_in_main']
    assert {'name': 'Windrest Peak', 'progress': 60} in mondstadt['areas']
    assert not any(r['name'] == 'Windrest Peak' for r in result['regions'])
    assert result['groups'] == [
        {'id': '1', 'name': 'Mondstadt', 'progress': 80},
        {'id': '17', 'name': 'Nod-Krai', 'progress': 90}]
    child = entry(21, 'Windrest Peak', 600, area_exploration_list=[])
    child['parent_id'] = 1
    nested = normalize_exploration([entry(1, 'Mondstadt', 800), child])
    assert nested['groups'][0]['progress'] == 80
    assert nested['regions'][0]['areas'][-1] == {'name': 'Windrest Peak', 'progress': 60}


def test_missing_zero_unknown_maps_and_image_policy():
    result = normalize_exploration([entry(1, 'Mondstadt', None), entry(2, 'Liyue', 0),
                                   entry(99, 'Future Map', 700)])
    assert [g['progress'] for g in result['groups']] == [None, 0, 70]
    assert allowed_image('https://act-webstatic.hoyoverse.com/game_record/genshin/city_icon/UI_ChapterIcon_Mengde.png')
    assert not allowed_image('https://act-webstatic.hoyoverse.com/other/secret.png')
    assert not allowed_image('https://act-webstatic.hoyoverse.com.evil.test/game_record/genshin/city_icon/a.png')


async def test_exploration_only_reads_selected_bound_account():
    adapter = HoYoLABClient(HoyoSettings(enabled=True, game_uid='812345678', cookies={'ltuid_v2': '1', 'ltoken_v2': 'test'}))
    adapter.client = SimpleNamespace(
        get_game_accounts=AsyncMock(return_value=[SimpleNamespace(uid=812345678, nickname='Tester', server='os_asia', level=60, game=genshin.Game.GENSHIN)]),
        _request_genshin_record=AsyncMock(return_value={'world_explorations': [entry(1, 'Mondstadt', 900)]}))
    result, _ = await adapter.explore()
    assert result['uid'] == '812345678' and result['groups'][0]['progress'] == 90
    adapter.client._request_genshin_record.assert_awaited_once_with('index', 812345678, lang='en-us')
    adapter.settings.game_uid = '823456789'
    with pytest.raises(HubError) as error:
        await adapter.explore()
    assert error.value.code == 'ACCOUNT_SELECTION_REQUIRED'
    assert adapter.client._request_genshin_record.await_count == 1
