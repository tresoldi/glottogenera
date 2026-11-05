# Genus names

A genus takes the name of its Glottolog node unless
[`../data/genus_names.tsv`](../data/genus_names.tsv) (kept in the package as
`src/glottogenera/data/genus_names.tsv`) gives another. The names are applied
after the genera are computed and do not affect them; they are keyed by node,
so `glottogenera.genus_name()` also names the genera at other thresholds, and
`genus_glottolog_name` keeps the Glottolog name.

## Policy

Every genus with more than one language was checked against four criteria,
and renamed only when one of them applies and the new name is unambiguous in
the dataset:

- **Glottolog label**: the name carries a label of Glottolog's bookkeeping
  rather than of the group, such as "linkage" for groups that descend from a
  dialect network; the label is dropped where the rest of the name is
  unambiguous.
- **WALS name**: the genus coincides with a WALS genus whose name differs, and
  that name is the established one. WALS names that cover more than the genus
  are not used, nor are those that differ from Glottolog's only in form.
- **Literature name**: the Glottolog name is a coinage or a list of members,
  and the specialist literature has a name for this group.
- **Misleading name**: the name suggests another group than the genus holds,
  such as a name used for a larger group, or an "Unclassified" node, which
  collects languages not yet placed within a family and is not a subgroup
  (such genera are named "X (unclassified)").

Names are not changed for taste: hyphenated lists of members, common in the
literature, are kept unless a criterion applies, and so are names for which no
established alternative is known. Each row of `genus_names.tsv` records the
criteria, a confidence, a rationale and its sources.

## Decisions

32 genera are renamed (`genus_names.tsv`). The cases below were considered and
decided as described.

**WALS name differs, Glottolog name kept**, because the Glottolog name is at
least as standard: Indo-Aryan (WALS Indic), Lolo-Burmese (Burmese-Lolo),
Sinitic (Chinese), Karenic (Karen), Nicobaric (Nicobarese), Digarish
(Digaroan), Hlaic (Hlai), Khmeric (Khmer), Chimbu-Wahgi (Chimbu), Paniai Lakes
(Wissel Lakes-Kemandoga), Ruboni (Mikarew), Yirram (Jaminjungan), Ngurlun
(Wambayan). Differences of spelling or suffix only: Moru-Madi (Moru-Ma'di),
Heibanic (Heiban), Tamaic (Taman), Dajuic (Daju), Lenduic (Lendu), Agaw
(Central Cushitic), Egyptian (Egyptian-Coptic), South Cushitic (Southern
Cushitic).

**WALS name broader than the genus, Glottolog name kept:** Ottilien (WALS
Lower Ramu), Oti-Volta (Northern-Central Gur), Fula (Peul-Serer), South Surmic
(Surmic), Khoe (Khoe-Kwadi), Northern North Halmahera (North Halmaheran),
Greater South Sulawesi (South Sulawesi; it is unclear whether WALS includes
the Rampi-Seko-Badaic languages).

**Names that look coined but are the literature's, kept:** West
Alor-Straits-Pantar (Kaiping & Klamer 2022), Nambikwara Complex (Eberhard
2009, for Northern plus Southern Nambikwara without Sabanê) and Bima-Lembata
(Fricke 2019). Bantu A-B10-B20-B30 is renamed North-West Bantu (Bostoen 2008,
for zone A with B10–B30; low confidence, as treatments differ over the Mbam
languages and B20).

**No established name, Glottolog name kept:** East Queensland Border Pama
Nyungan (Central East Coast is larger), Southwestern Alaya-Athima (Kunjen is
also a member's name and may not include Athima), Continental Transalpine
Celtic (Transalpine Celtic and Gaulish vary in scope).

**Kept because the alternative would mislead:**
- Madak linkage, Buang linkage: dropping "linkage" gives the name of a member
  language (Madak) or of only part of the group (Buang).
- Nuclear Angan, Nuclear Sentanic, Iwaidjan Proper: dropping the qualifier
  gives the family name, but the family also has languages outside the genus.
- Enga-Kewa-Huli: "Engan" is also the name of a narrower child node.
- Pidjanan: WALS "Wapishanan" is the name of a child node.
- Tarahumara-Guarijio: WALS "Tarahumaran" is the name of a child node.
- Qom (Toba, Pilagá, Mocoví): "Qom" may suggest Toba alone, but "Southern
  Guaicuruan" would also include Abipón, a separate genus.
- North Bougainville Oceanic: it keeps the group apart from the Papuan North
  Bougainville family.

**Kept because the alternatives are uncertain:** Koro-Holon (whether Milang is
"Holon"), Dhimal-Lhokpu-Toto (whether WALS Dhimalic includes Lhokpu),
Brahmaputran (van Driem) against Sal (Burling), Ta-Ne-Omotic (Glottolog also
gives Gonga-Gimojan; WALS North Omotic is broader).

**Renamed although the new name is also a member's:** Hungaric → Hungarian,
Khantyic → Khanty and Mansic → Mansi follow the handbook's usage, and Tabar
linkage → Tabar (also another name of Mandara, medium confidence). Elsewhere
such names are avoided (Madak, Qom).

**Families renamed:** whole families normally keep their names, but Tsimshian
becomes Tsimshianic, since the name is also that of a member language, and
Narrow Talodi becomes Talodi, the WALS name and that of Norton & Alaki.
