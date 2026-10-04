# Arsip build Teyvat

Direction from the supplied redesign PRD; implementation assumption pending any user steering. The brief's specific direction takes precedence over the concept seed. Operate mode: choose a character and read its build before secondary tasks.

Dark ink #101719, reading surfaces #182225, raised #213034, parchment text #F1EFE7, secondary #B5C0BE, gold #D8BB78. Existing amber maps to gold; green maps to #9BCCAA without changing configuration values.

Georgia headings and system sans body, locally licensed JetBrains Mono for UID only. Body 16px, metadata 13px; 4/8/12/16/24/32/48 spacing. Sidebar 224px; native modal navigation on mobile. Portrait grid, separate build destination, flat artifact rows, ranking table, resource list, three settings groups.

Assets: existing metadata portrait URLs served through the image proxy; dimensions reserved with CSS, no new remote splash artwork. Missing image uses initial and visible name. JetBrainsMono.woff2 retains static/fonts/OFL.txt. Provider images are used as returned by the existing integration; external dimensions vary and are not asserted as measured.

Motion: color/border 160ms, dialog reveal 180ms; reduced motion disables animation. No delayed content, decorative charts or invented data. Back restores showcase filters, page, scroll and character focus.
