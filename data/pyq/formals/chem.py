"""Formalizations of the 100 ascent chemistry questions (data/pyq/ascent_chem.jsonl).

Engines: chem_property (cqse/chemistry/rules.py, versioned rule set), equation_system (calculations),
statement_set (option formats). Statement truths are COMPUTED by the rule engine wherever it covers the fact;
descriptive chemistry is CURATED (teacher must confirm). Formals model the STEM; option values come from the
option text. Image-only questions are omitted (listed in IMAGE_ONLY with the reason).
"""

K = lambda v, u="": {"value": v, "unit": u}  # noqa: E731
U = lambda u="", d="real": {"unit": u, "domain": d}  # noqa: E731


def CP(**k):
    return {"kind": "chem_property", **k}


def V(p, s, **k):
    return {"query": "value", "property": p, "species": s, **k}


def T(sub, claim):
    """Computed truth: sub-query evaluated by the chemistry rule engine."""
    f = sub if "kind" in sub else CP(**sub)
    return {"formal": f, "claim": claim, "subject": "CHEMISTRY"}


def C(truth, note):
    return {"truth": truth, "basis": "curated", "note": note}


def ALL(*checks, **extra):
    return CP(query="all", checks=list(checks), **extra)


def chk(p, s, claim, **k):
    return {**V(p, s, **k), "claim": claim}


def SEL(statements):
    return {"kind": "statement_set", "format": "select_combination", "statements": statements}


def PAIR(t1, t2):
    return {"kind": "statement_set", "format": "statement_pair", "statements": {"I": t1, "II": t2}}


def MATCH(pairs):
    return {"kind": "statement_set", "format": "match_list", "pairs": pairs}


ONE = {"A": "{1}", "B": "{2}", "C": "{3}", "D": "{4}"}   # single-answer MCQ modelled as "which option is true"
NCERT = "NCERT XII"


FORMALS = {
    # ------------------------------------------------------------------ chemical bonding
    "m6ulvpaf": {
        "formal": SEL({
            "A": T(ALL(*[chk("hybridization", s, "== sp3") for s in ("H2O", "NH3", "CH4")]), "== 1"),
            "B": C(True, "experimental bond angles H2O 104.5, NH3 107.5 (NCERT XI 4.6: 107), CH4 109.5"),
            "C": C(True, "TEXT DEFECT: statement C is truncated in the extraction ('CH4 ...' - the '<' chain was "
                         "lost). Presumed CH4 < NH3 < H2O, which is true; teacher must check the source"),
            "D": C(False, "H2O and NH3 are Lewis bases (lone pairs); CH4 is neither"),
            "E": C(False, "in NH3(aq) NH3 is the Bronsted base and H2O the acid - roles reversed"),
        }),
        "note": "A computed (VSEPR); B-E curated; statement C text truncated in source extraction"},
    "m6w9nzt0": {
        "formal": SEL({k: T(ALL(chk("shape", a, "== square_pyramidal"), chk("shape", b, "== square_pyramidal")),
                            "== 1")
                       for k, (a, b) in {"A": ("BrF5", "PCl5"), "B": ("SbF5", "PCl5"), "C": ("BrF5", "XeOF4"),
                                         "D": ("SbF5", "XeOF4")}.items()}),
        "option_values": ONE, "note": "VSEPR shapes of both members of each pair"},
    "m6qvb5mn": {
        "formal": CP(query="count", property="is_linear",
                     species=["SO2", "BeCl2", "CO2", "N3^-", "NO2", "F2O", "XeF2", "NO2^+", "I3^-", "O3"],
                     claim="== 1"),
        "note": "explanation's list is an image; no explanation value available"},
    "m6ulvpvl": {
        "formal": SEL({k: T(V("lcao_symmetry_match", p), "== 1") for k, p in
                       {"A": "2pz|2px", "B": "2s|2px", "C": "3dxy|3dx2-y2", "D": "2s|2pz",
                        "E": "2pz|3dx2-y2"}.items()}),
        "note": "LCAO allowed iff same symmetry about the internuclear (z) axis"},
    "m6w9nzrv": {
        "formal": SEL({k: T(CP(query="expr", expr="x - n", terms={
            "x": V("unpaired_electrons", ion), "n": V("lone_pairs_equatorial", "ClF3")}), "== 0")
            for k, ion in {"A": "V^3+", "B": "Ti^3+", "C": "Cu^2+", "D": "Ni^2+", "E": "Ti^2+"}.items()}),
        "note": "n = equatorial lone pairs of ClF3 = 2"},
    "m9gxges1": {
        "formal": PAIR(C(True, "cellulose -OH groups H-bond water strongly; cotton dries slower"),
                       C(False, "nylon forms fewer H-bonds with water than cellulose")),
        "note": "descriptive"},
    "m9ghxnoz": {
        "formal": SEL({k: T(V("paramagnetic", s), "== 1") for k, s in
                       {"A": "O2", "B": "N2", "C": "F2", "D": "S2", "E": "Cl2"}.items()}),
        "note": "MO theory; S2/Cl2 treated as O2/F2 analogues (3s/3p)"},
    "m6rp62gr": {
        "formal": {"kind": "statement_set", "format": "ordering", "order": {
            "items": ["HBr", "H2S", "NF3", "CHCl3"],
            "values": {"HBr": "0.82", "H2S": "0.97", "NF3": "0.234", "CHCl3": "1.04"},
            "direction": "increasing", "basis": "curated",
            "note": "experimental gas-phase dipole moments (D), CRC Handbook: HBr 0.82, H2S 0.97, NF3 0.234, CHCl3 1.04"}},
        "option_values": {"A": "1234", "B": "2134", "C": "3124", "D": "4312"},
        "note": "experimental data, curated"},
    "m6v42g9h": {
        "formal": PAIR(C(True, "O3: both O-O equal (resonance), between O=O and O-O"),
                       C(False, "equal intermediate bond length is due to resonance, not lp-lp repulsion")),
        "note": "descriptive (NCERT XI 4.5)"},
    "m9em61gf": {
        "formal": SEL({k: T(ALL(chk("hybridization", "SO2", f"== {a}"), chk("hybridization", "NO2^-", f"== {b}"),
                                chk("hybridization", "N3^-", f"== {c}")), "== 1")
                       for k, (a, b, c) in {"A": ("sp2", "sp2", "sp2"), "B": ("sp", "sp2", "sp"),
                                            "C": ("sp2", "sp", "sp"), "D": ("sp2", "sp2", "sp")}.items()}),
        "option_values": ONE, "note": "VSEPR hybridization"},
    "m9e5j4f8": {
        "formal": SEL({k: T(ALL(chk("hybridization", s, "== sp3d"), chk("bond_sites_inequivalent", s, "== 1"),
                                chk("lone_pairs", s, "> 0")), "== 1")
                       for k, s in {"A": "XeF4", "B": "XeF2", "C": "PF5", "D": "SF4"}.items()}),
        "option_values": ONE,
        "note": "different bond lengths <=> bonds on symmetry-inequivalent sites (axial vs equatorial)"},
    "m9e5j9ov": {
        "formal": MATCH({
            "A": ["III", T(ALL(chk("bond_pairs_total", "ICl2^-", "== 2"), chk("lone_pairs", "ICl2^-", "== 3")), "== 1")],
            "B": ["IV", T(ALL(chk("bond_pairs_total", "H2O", "== 2"), chk("lone_pairs", "H2O", "== 2")), "== 1")],
            "C": ["II", T(ALL(chk("bond_pairs_total", "SO2", "== 4"), chk("lone_pairs", "SO2", "== 1")), "== 1")],
            "D": ["I", T(ALL(chk("bond_pairs_total", "XeF4", "== 4"), chk("lone_pairs", "XeF4", "== 2")), "== 1")]}),
        "note": "List-II counts pi bond pairs: SO2 4:1 = 2 sigma + 2 pi (expanded-octet S=O structure, NCERT); "
                "sigma-only counting would give 2:1, which is not in List-II"},
    "m6qlgmot": {
        "formal": CP(**V("lewis_nonbonded_electrons", "NO2^-")), "explanation_value": "12",
        "note": "Lewis structure O=N-O(-)"},
    "m6srn66j": {
        "formal": MATCH({
            "A": ["IV", T(ALL(chk("octet_class", "CCl4", "== obeys"), chk("octet_class", "CO2", "== obeys")), "== 1")],
            "B": ["II", T(ALL(chk("octet_class", "BCl3", "== incomplete"),
                              chk("octet_class", "AlCl3", "== incomplete")), "== 1")],
            "C": ["I", T(ALL(chk("octet_class", "NO", "== odd"), chk("octet_class", "NO2", "== odd")), "== 1")],
            "D": ["III", T(ALL(chk("octet_class", "H2SO4", "== expanded"),
                               chk("octet_class", "PCl5", "== expanded")), "== 1")]}),
        "note": "Lewis-structure octet classification (NCERT XI 4.3 conventions; AlCl3 as monomer)"},
    "m9dunozb": {
        "formal": SEL({k: T(CP(query="pick", species=["SO2", "NF3", "NH3", "XeF2", "ClF3", "SF4"],
                               where=[{"property": "dipole_nonzero", "claim": "== 1"}], maximize="lone_pairs",
                               then={"property": "hybridization"}), f"== {h}")
                       for k, h in {"A": "sp3", "B": "dsp2", "C": "sp3d2", "D": "sp3d"}.items()}),
        "option_values": ONE, "note": "filter non-zero dipole, maximise central lone pairs (ClF3), hybridization"},
    "m9duns8v": {
        "formal": SEL({k: T(CP(**V("shape", "XeOF4"), premises=[{
            "statement": "A = Xe (rarest stable noble gas, lowest IE of A, X, Y), X = F, Y = O -> AX4Y = XeOF4",
            "basis": "curated"}]), f"== {sh}")
            for k, sh in {"A": "pentagonal_planar", "B": "square_pyramidal", "C": "trigonal_bipyramidal",
                          "D": "octahedral"}.items()}),
        "option_values": ONE, "note": "identification of XeOF4 curated; shape computed"},

    # ------------------------------------------------------------------ d and f block
    "m9ghxn8x": {
        "formal": SEL({k: T(CP(query="expr", expr="x - y", terms={"x": V("unpaired_electrons", a),
                                                                   "y": V("unpaired_electrons", b)}), "== 0")
                       for k, (a, b) in {"A": ("Ti^3+", "Mn^2+"), "B": ("Ti^2+", "Co^2+"), "C": ("Fe^3+", "Cr^2+"),
                                         "D": ("V^2+", "Co^2+")}.items()}),
        "option_values": ONE, "note": "free-ion high-spin unpaired electrons"},
    "m6ulv930": {
        "formal": SEL({"A": C(False, "Lu3+ 4f14, stable, not oxidising"), "B": C(False, "Eu2+ is a reductant"),
                       "C": C(True, "Tb4+ (4f7) is a strong oxidant, reverts to Tb3+ (NCERT XII 8.5)"),
                       "D": C(False, "Ce3+ is not an oxidant; Ce4+ is")}),
        "option_values": ONE, "note": "descriptive lanthanoid chemistry"},
    "m9gxgbh6": {
        "formal": CP(query="pick", species=["Sc", "Mn", "Co", "Cu"], maximize="enthalpy_atomisation",
                     then={"property": "spin_only_moment", "species_template": "{X}^2+"}),
        "explanation_value": "4",
        "note": "enthalpies of atomisation from NCERT XII Table 8.2 (Co 425 highest); Co2+ d7 -> sqrt(15) = 3.87"},
    "m6w9nzr0": {
        "formal": SEL({
            "A": T(ALL(chk("oct_config_ligand_independent", "Cr^3+", "== 1"),
                       {"curated": False, "note": "Cr gives a green borax bead, not violet"}), "== 1"),
            "B": T(ALL(chk("oct_config_ligand_independent", "Ti^3+", "== 1"),
                       {"curated": False, "note": "Ti bead is colourless in the oxidising (non-luminous) flame"}),
                   "== 1"),
            "C": T(ALL(chk("oct_config_ligand_independent", "Ni^2+", "== 1"),
                       {"curated": True, "note": "Ni gives violet (hot) / brown (cold) bead in oxidising flame"}),
                   "== 1"),
            "D": T(ALL(chk("oct_config_ligand_independent", "Mn^2+", "== 1"),
                       {"curated": True, "note": "Mn gives an amethyst/violet bead in oxidising flame"}), "== 1")}),
        "option_values": ONE,
        "note": "ligand-independence computed (Oh high- vs low-spin filling); bead colours curated"},
    "m9fnus9d": {
        "formal": CP(**V("terminal_oxygens", "Cr2O7^2-"), premises=[{
            "statement": "A = dichromate (chromyl chloride test); B = Na2CrO4; C = Na2Cr2O7 (acidified chromate)",
            "basis": "curated"}]),
        "explanation_value": "6", "note": "reaction identification curated; O count computed"},
    "m9gxgc8q": {
        "formal": PAIR(C(True, "CrO3 is a stronger oxidant than MoO3 (Cr(VI) less stable)"),
                       C(False, "higher oxidation states are more stable down the group: Mo(VI) > Cr(VI)")),
        "note": "descriptive (NCERT XII 8.3)"},
    "m9e5j9s5": {
        "formal": SEL({"A": C(True, "M = V (highest atomisation, NCERT T8.2); green aquated ion V3+; V2O3 basic"),
                       "B": C(False, "V2O3 is not neutral"), "C": C(False, "V2O3 is basic, not amphoteric"),
                       "D": C(False, "V2O3 is basic, not acidic")}),
        "option_values": ONE, "note": "oxide acid-base nature curated"},
    "m6ulvplb": {
        "formal": SEL({"A": C(False, ""), "B": C(False, ""),
                       "C": C(True, "2MnO2 + 4KOH + O2/KNO3 -> 2K2MnO4 (NCERT XII 8.7)"), "D": C(False, "")}),
        "option_values": ONE, "note": "descriptive"},
    "m9duiucn": {
        "formal": {"kind": "statement_set", "format": "ordering", "order": {
            "items": ["Cu^+", "Cu^2+", "Cr^2+", "Cr^3+"],
            "values": {s: {"formal": CP(**V("spin_only_moment", s)), "subject": "CHEMISTRY"}
                       for s in ["Cu^+", "Cu^2+", "Cr^2+", "Cr^3+"]},
            "direction": "decreasing", "basis": "rule: cqse-chem-rules 1.0 spin-only moment"}},
        "option_values": {"A": "4312", "B": "1243", "C": "3421", "D": "2134"},
        "note": "values computed by the rule engine"},
    "m9fnus4d": {
        "formal": SEL({k: T(V("spin_only_moment", s, round_to="0.1"), "== 4.9") for k, s in
                       {"A": "Cr^2+", "B": "Fe^2+", "C": "Fe^3+", "D": "Co^2+", "E": "Mn^3+"}.items()}),
        "note": "sqrt(24) = 4.899 -> 4.9"},
    "m6v42tdx": {
        "formal": MATCH({l: [r, T(CP(query="approx", property="spin_only_moment", species=s, target=t, tol="0.02"),
                                  "== 1")]
                         for l, (s, r, t) in {"A": ("Ti^3+", "III", "1.73"), "B": ("V^2+", "I", "3.87"),
                                              "C": ("Ni^2+", "IV", "2.84"), "D": ("Sc^3+", "II", "0")}.items()}),
        "option_values": {"A": "3142", "B": "2413", "C": "3124", "D": "4231"},
        "note": "printed 2.84 for sqrt(8) = 2.828 (tolerance 0.02; List-II values are well separated)"},
    "m6t9yfuy": {
        "formal": SEL({"A": C(False, ""), "B": C(False, ""),
                       "C": C(True, "dichromate + KOH -> chromate (A); chromate + H2SO4 -> dichromate (B) + K2SO4"),
                       "D": C(False, "")}),
        "option_values": ONE, "note": "chromate-dichromate equilibrium (NCERT XII 8.7)"},
    "m6t9xwuz": {
        "formal": MATCH({"A": ["IV", C(True, "bronze Cu-Sn")], "B": ["III", C(True, "brass Cu-Zn")],
                         "C": ["I", C(True, "UK 'silver' coin cupronickel Cu-Ni")],
                         "D": ["II", C(True, "stainless steel Fe, Cr, Ni, C")]}),
        "note": "descriptive"},
    "m6srmtnf": {
        "formal": SEL({k: T(CP(query="all_equal", property="aq_colour", species=sp_), "== 1")
                       for k, sp_ in {"A": ["V^2+", "Cr^3+", "Mn^3+"], "B": ["Ti^4+", "V^4+", "Mn^2+"],
                                      "C": ["Sc^3+", "Ti^3+", "Cr^2+"], "D": ["Zn^2+", "V^3+", "Fe^3+"]}.items()}),
        "option_values": ONE, "note": "NCERT XII table of colours of aquated 3d ions"},
    "m6rp6jyr": {
        "formal": CP(query="expr", expr="x + y", terms={"x": V("subshell_electrons", "Nb", subshell="4d"),
                                                         "y": V("subshell_electrons", "Ru", subshell="4d")}),
        "explanation_value": "11", "note": "Nb 4d4 5s1, Ru 4d7 5s1 (tabulated exceptions)"},
    "m6qvb8sd": {
        "formal": SEL({k: T(V("subshell_electrons", s, subshell="4f"), "== 7") for k, s in
                       {"A": "Eu^2+", "B": "Gd^3+", "C": "Eu^3+", "D": "Tb^3+", "E": "Sm^2+"}.items()}),
        "note": "4f^n of lanthanoid ions"},
    "m6qrgsyy": {
        "formal": CP(**V("molar_mass", "Fe2O3"), premises=[{
            "statement": "4FeCr2O4 + 8Na2CO3 + 7O2 -> 8Na2CrO4 + 2Fe2O3 + 8CO2; water-insoluble product Fe2O3",
            "basis": "curated (NCERT XII 8.7)"}]),
        "explanation_value": "160", "note": "atomic masses not given in stem: IUPAC values used"},
    "m6qpcoxo": {
        "formal": SEL({"A": C(False, "Fe > Mn"), "B": C(False, "Fe > Mn"), "C": C(False, "Re (3459 K) > Os (3306 K)"),
                       "D": C(True, "mp: Mn 1519 < Fe 1811 K; Tc 2430 < Ru 2607 K; Os 3306 < Re 3459 K")}),
        "option_values": ONE, "note": "melting-point data curated"},
    "m6rlt43b": {
        "formal": CP(**V("oxidation_state", "VO4^3-", element="V"), premises=[{
            "statement": "the amphoteric oxide is V2O5; with alkali it gives vanadate VO4^3-", "basis": "curated"}]),
        "option_values": {"A": "4", "B": "5", "C": "3", "D": "7"}, "note": "oxidation state computed"},

    # ------------------------------------------------------------------ biomolecules
    "m6rlr6nx": {
        "formal": MATCH({"A": ["III", C(True, "sucrose: alpha1-beta2")], "B": ["I", C(True, "maltose: alpha1-4")],
                         "C": ["IV", C(True, "lactose: beta1-4")],
                         "D": ["II", C(True, "amylopectin: alpha1-4 and alpha1-6")]}),
        "note": f"{NCERT} Ch.10"},
    "m6srmyge": {
        "formal": PAIR(C(True, "fructose reduces Tollens' reagent"),
                       C(True, "in base fructose isomerises (enediol) to glucose/mannose")),
        "note": "descriptive"},
    "m9e5j4cy": {
        "formal": {"kind": "equation_system", "knowns": {}, "unknowns": {"t": U("", "natural")},
                   "equations": ["t = 4*3*2*1"], "target": "t",
                   "model": ["each of the four distinct residues used once: 4! sequences"]},
        "option_values": {"A": "32", "B": "24", "C": "8", "D": "16"}, "note": "permutations"},
    "m9gxgbtk": {
        "formal": SEL({"A": C(False, "B1 water-soluble"), "B": C(False, "C water-soluble"),
                       "C": C(True, "E fat-soluble"), "D": C(False, "B12 water-soluble"),
                       "E": C(True, "K fat-soluble")}),
        "note": "fat-soluble vitamins A, D, E, K"},
    "m6qp1wim": {
        "formal": MATCH({"A": ["IV", C(True, "amylose alpha C1-C4, plant")], "B": ["I", C(True, "cellulose beta C1-C4")],
                         "C": ["II", C(True, "glycogen alpha C1-C4, animal")],
                         "D": ["III", C(True, "amylopectin alpha 1-4 and 1-6, plant")]}),
        "note": "descriptive"},
    "m6rlxhp4": {
        "formal": SEL({"A": C(False, "starch -> glucose"), "B": C(True, "sucrose -> glucose + fructose"),
                       "C": C(True, "lactose -> glucose + galactose"), "D": C(False, "amylopectin -> glucose only"),
                       "E": C(True, "amylose -> glucose")}),
        "note": "descriptive"},
    "m9e5ja7r": {
        "formal": PAIR(C(False, "fructose in sucrose is D-(-)-fructose, not D-(+)"),
                       C(True, "sucrose hydrolysis gives invert sugar")),
        "note": "descriptive"},
    "m9ghxnwx": {
        "formal": CP(**V("dna_duplex_hbonds", "GGCAAATCGGCTA")), "explanation_value": "33",
        "note": "sequence from the stem; G-C 3, A-T 2"},
    "m9dunnwm": {
        "formal": SEL({"A": C(False, "isoleucine/threonine have two chiral centres"),
                       "B": C(True, "cysteine -SH forms disulfide dimer (cystine)"),
                       "C": C(False, "aspartic acid also has side-chain COOH"),
                       "D": C(False, "glycine is optically inactive")}),
        "option_values": ONE, "note": "descriptive"},
    "m6w9o4nh": {
        "formal": PAIR(C(False, "glucose pentaacetate has no free CHO: no 2,4-DNP reaction"),
                       C(True, "starch + dil. H2SO4 at 393 K / 2-3 atm gives glucose (NCERT)")),
        "note": "descriptive"},
    "m9elqyz2": {
        "formal": PAIR(C(False, "proteins give alpha-amino acids, not beta"),
                       C(False, "fibrous proteins are already water-insoluble; statement misdescribes denaturation")),
        "note": "descriptive"},
    "m6ulvdu9": {
        "formal": SEL({"A": C(True, "pentose"), "B": C(False, "furanose form in nucleic acids"),
                       "C": C(True, "D-configuration"), "D": C(True, "reducing sugar when free"),
                       "E": C(False, "beta-anomer in nucleic acids")}),
        "note": "STEM DEFECT: 'ribose present in DNA' - DNA contains 2-deoxyribose; truths hold for both"},
    "m6qk2aop": {
        "formal": SEL({"A": C(True, "valine essential"), "B": C(False, "proline non-essential"),
                       "C": C(True, "lysine essential"), "D": C(True, "threonine essential"),
                       "E": C(False, "tyrosine non-essential")}),
        "note": f"{NCERT} Table 10.2"},
    "m6t9xwyg": {
        "formal": SEL({"A": C(False, ""), "B": C(False, ""), "C": C(False, ""),
                       "D": C(True, "alpha-helix and beta-pleated sheet are secondary structure")}),
        "option_values": ONE, "note": "descriptive"},
    "m6qvbrfa": {
        "formal": SEL({"A": C(False, ""), "B": C(True, "ascorbic acid = vitamin C"), "C": C(False, ""),
                       "D": C(False, "")}),
        "option_values": ONE, "note": "descriptive"},

    # ------------------------------------------------------------------ nitrogen compounds
    "m9dunrnc": {
        "formal": {"kind": "statement_set", "format": "ordering", "order": {
            "items": ["NH3", "N2H4", "EtNH2", "Et2NH", "Et3N"],
            "values": {"NH3": "-4.75", "N2H4": "-5.9", "EtNH2": "-3.29", "Et2NH": "-3.00", "Et3N": "-3.25"},
            "direction": "increasing", "basis": "curated",
            "note": "basicity = -pKb (aq): NCERT XII Table 13.3 for NH3 and ethylamines; hydrazine pKb ~5.9 (lit.)"}},
        "option_values": {"A": "12534", "B": "21534", "C": "21354", "D": "12345"},
        "note": "experimental pKb data, curated"},
    "m9e5j4rt": {
        "formal": CP(query="expr", expr="M/10", unit="g", terms={"M": V(
            "molar_mass", "C16H13N3O3S", atomic_masses={"H": 1, "C": 12, "N": 14, "O": 16, "S": 32})},
            premises=[{"statement": "diazotised sulphanilic acid couples with 1-naphthylamine: red azo dye "
                                    "4-(4-amino-1-naphthylazo)benzenesulfonic acid, C16H13N3O3S",
                       "basis": "curated"}],
            options_rounded={"rel_tol": "0.02"}),
        "option_values": {"A": "330", "B": "33", "C": "343", "D": "66"},
        "note": "0.1 mol x 327 g/mol = 32.7 g; printed option 33 (rounded)"},
    "m6rm3m6z": {
        "formal": SEL({"A": C(False, "primary amines DO give diazonium salts"), "B": C(True, "carbylamine reaction"),
                       "C": C(False, "only primary amines give carbylamine test"),
                       "D": C(True, "benzenesulfonyl chloride = Hinsberg's reagent"),
                       "E": C(False, "tertiary amines do not react with benzenesulfonyl chloride")}),
        "note": "descriptive"},
    "m6ulvjab": {
        "formal": PAIR(C(True, "Dumas method estimates nitrogen"),
                       C(False, "ammonium sulphate formation is Kjeldahl's method")),
        "note": "descriptive"},

    # ------------------------------------------------------------------ electrochemistry
    "m9e5j5ry": {
        "formal": {"kind": "equation_system",
                   "knowns": {"w": K("0.2", "g"), "Vs": K("100", "mL"), "M": K("40", "g/mol"),
                              "rho": K("870", "mohm*m"), "u": K("100", "mS*dm^2/mol")},
                   "unknowns": {"c": U("mol/m^3", "positive"), "L": U("S*m^2/mol", "positive"), "x": U("", "positive")},
                   "equations": ["c*M*Vs = w", "L*rho*c = 1", "L = x*u"], "target": "x",
                   "model": ["Lambda_m = kappa/c, kappa = 1/rho", "M(NaOH) = 40 g/mol (not stated in stem)"]},
        "explanation_value": "23", "note": "molar conductivity"},
    "m9fnus6t": {
        "formal": {"kind": "statement_set", "format": "ordering", "order": {
            "items": ["H^+", "Na^+", "K^+", "Ca^2+", "Mg^2+"],
            "values": {"H^+": "349.6", "Na^+": "50.1", "K^+": "73.5", "Ca^2+": "119.0", "Mg^2+": "106.0"},
            "direction": "decreasing", "basis": "curated",
            "note": "limiting molar conductivities at 298 K, S cm2/mol (NCERT XII Table 2.4)"}},
        "option_values": {"A": "12345", "B": "14532", "C": "51432", "D": "12453"}, "note": "data, curated"},
    "m9fbg4fr": {
        "formal": PAIR(C(True, "deposition in order of decreasing E0: Ag (0.80) > Hg (0.79) > Cu (0.24)"),
                       C(False, "water is reduced to H2 (not O2) at the cathode; O2 forms at the anode")),
        "note": "electrolysis rules, curated"},
    "m9ghxnaj": {
        "formal": CP(query="expr", expr="1000*x1 + 100*y1 + 10*x2 + y2", terms={
            "x1": V("oxidation_state", "PbSO4", element="Pb"), "y1": V("oxidation_state", "PbO2", element="Pb"),
            "x2": V("oxidation_state", "PbSO4", element="Pb"), "y2": V("oxidation_state", "Pb", element="Pb")},
            premises=[{"statement": "charging (electrolytic) mode, IUPAC convention: anode = oxidation "
                                    "PbSO4 -> PbO2, cathode = reduction PbSO4 -> Pb", "basis": "curated"}]),
        "option_values": {"A": "242", "B": "2004", "C": "4202", "D": "2024"},
        "note": "options encoded as 1000*x1+100*y1+10*x2+y2. Under the IUPAC convention (anode = oxidation) the "
                "answer (+2,+4,+2,0) matches NO option; key D (+2,0,+2,+4) uses discharge-mode electrode names"},
    "m6qkqo0m": {
        "formal": MATCH({"A": ["III", C(True, "transistors: dry (Leclanche) cell")],
                         "B": ["I", C(True, "hearing aids: mercury cell")],
                         "C": ["IV", C(True, "inverters: lead storage battery")],
                         "D": ["II", C(True, "Apollo: H2-O2 fuel cell")]}),
        "note": "descriptive"},
    "m6qlella": {
        "formal": SEL({"A": C(False, "Ag anode dissolves; no O2"), "B": C(True, "Pt anode: water oxidised to O2"),
                       "C": C(True, "dil. H2SO4: O2 at anode"),
                       "D": C(False, "conc. H2SO4: HSO4- oxidised to S2O8 2- (NCERT)")}),
        "note": "descriptive"},
    "m6qoow0u": {
        "formal": SEL({k: T(CP(query="nernst", anode={"ox": "Mg^2+", "red": "Mg"}, cathode={"ox": "Ag^+", "red": "Ag"},
                               symbols={"Mg^2+": "Mg", "Ag^+": "Ag"}), claim)
                       for k, claim in {"A": "== -R*T*log(Ag)/F + R*T*log(Mg)/(2*F)",
                                        "B": "== -R*T*log(Mg)/(2*F) + R*T*log(Ag)/(2*F)",
                                        "C": "== -R*T*log(Ag)/(2*F) + R*T*log(Mg)/(2*F)",
                                        "D": "== R*T*log(Ag)/F - R*T*log(Mg)/(2*F)"}.items()}),
        "option_values": ONE, "note": "each option's E - E0 written with logs expanded (Ag = [Ag+], Mg = [Mg2+])"},
    "m6qp5l8v": {
        "formal": SEL({"A": C(False, ""), "B": C(True, "weak electrolyte: Lambda_m falls steeply as c increases"),
                       "C": C(False, ""), "D": C(False, "")}),
        "option_values": ONE, "note": "descriptive (NCERT XII 2.4)"},
    "m6qpiv13": {
        "formal": CP(query="redox_extremum", role="oxidising",
                     couples=[{"ox": "Sn^4+", "red": "Sn^2+", "E": "1.15"}, {"ox": "Al^3+", "red": "Al", "E": "-1.66"},
                              {"ox": "Pb^4+", "red": "Pb^2+", "E": "1.67"}, {"ox": "Tl^3+", "red": "Tl", "E": "1.26"}],
                     candidates={"A": "Sn^4+", "B": "Al^3+", "C": "Pb^4+", "D": "Tl^3+"}),
        "option_values": ONE, "note": "highest E0(red) -> strongest oxidant"},
    "m6qvb15l": {
        "formal": SEL({"A": C(True, "peroxodisulphuric acid by electrolysis of conc. H2SO4 (2HSO4- -> H2S2O8 + 2e-)"),
                       "B": C(False, ""), "C": C(False, ""), "D": C(False, "dilute acid gives O2")}),
        "option_values": ONE, "note": "descriptive"},
    "m6qvbchf": {
        "formal": {"kind": "equation_system",
                   "knowns": {"I": K("2", "A"), "t": K("30", "min"), "M": K("27", "g/mol"), "F": K("96500", "C/mol"),
                              "z": K("3")},
                   "unknowns": {"m": U("g", "positive")}, "equations": ["m*z*F = I*t*M"], "target": "m",
                   "model": ["Al3+ + 3e- -> Al; 100% current efficiency"], "options_rounded": {"rel_tol": "0.01"}},
        "option_values": {"A": "1.660", "B": "1.007", "C": "0.336", "D": "0.441"}, "note": "Faraday's law"},
    "m6rp6jes": {
        "formal": PAIR(C(True, "corrosion is electrochemical; purer (more active) region anodic, impurity cathodic"),
                       C(False, "corrosion is faster in acidic medium")),
        "note": "descriptive"},
    "m6rmra42": {
        "formal": {"kind": "equation_system",
                   "knowns": {"V": K("600", "mL"), "c": K("0.01", "mol/L"), "t": K("5", "min"), "F": K("96500", "C/mol")},
                   "unknowns": {"I": U("A", "positive")}, "equations": ["I*t = c*V*F"], "target": "I",
                   "model": ["pH 12 -> [OH-] = 0.01 M produced; 1 e- per OH-; initial OH- (pH 7) neglected"]},
        "explanation_value": "2", "note": "I = 1.93 A"},
    "m6srmyb5": {
        "formal": CP(query="combine_potentials",
                     couples=[{"ox": "FeO4^2-", "red": "Fe^3+", "n": 3, "E": "2.0"},
                              {"ox": "Fe^3+", "red": "Fe^2+", "n": 1, "E": "0.8"},
                              {"ox": "Fe^2+", "red": "Fe", "n": 2, "E": "-0.5"}],
                     target={"ox": "FeO4^2-", "red": "Fe^2+"}),
        "option_values": {"A": "1.2", "B": "2.1", "C": "1.4", "D": "1.7"}, "note": "Latimer diagram; n checked by oxidation states"},
    "m6t9yeyy": {
        "formal": CP(query="extremum", select="min", rule="most negative dG0 = -nFE0cell", values={
            k: {"query": "cell", "return": "deltaG_over_F", "anode": a, "cathode": c}
            for k, (a, c) in {
                "A": ({"ox": "Zn^2+", "red": "Zn", "E": "-0.76"}, {"ox": "Ag^+", "red": "Ag", "E": "0.80"}),
                "B": ({"ox": "Ag^+", "red": "Ag", "E": "0.80"}, {"ox": "Mg^2+", "red": "Mg", "E": "-2.37"}),
                "C": ({"ox": "Zn^2+", "red": "Zn", "E": "-0.76"}, {"ox": "Mg^2+", "red": "Mg", "E": "-2.37"}),
                "D": ({"ox": "Cu^2+", "red": "Cu", "E": "0.34"}, {"ox": "Ag^+", "red": "Ag", "E": "0.80"})}.items()}),
        "option_values": ONE, "note": "cells as written: left = anode, right = cathode"},
    "m6ulv91f": {
        "formal": SEL({k: T(CP(query="combine_potentials",
                               couples=[{"ox": "Ag^+", "red": "Ag", "n": 1, "E": "x"},
                                        {"ox": "Fe^2+", "red": "Fe", "n": 2, "E": "y"},
                                        {"ox": "Fe^3+", "red": "Fe", "n": 3, "E": "z"}],
                               cell={"cathode": {"ox": "Ag^+", "red": "Ag"}, "anode": {"ox": "Fe^3+", "red": "Fe^2+"}}),
                            claim)
                       for k, claim in {"A": "== x + 2*y - 3*z", "B": "== x + 2*y", "C": "== y - 2*x",
                                        "D": "== x + y - z"}.items()}),
        "option_values": ONE, "note": "dG additivity: E(Fe3+/Fe2+) = 3z - 2y"},
    "m6v42ikg": {
        "formal": CP(query="redox_extremum", role="reducing",
                     couples=[{"ox": "Cr2O7^2-", "red": "Cr^3+", "E": "1.33"}, {"ox": "Cl2", "red": "Cl^-", "E": "1.36"},
                              {"ox": "MnO4^-", "red": "Mn^2+", "E": "1.51"}, {"ox": "Cr^3+", "red": "Cr", "E": "-0.74"}],
                     candidates={"A": "Cl^-", "B": "MnO4^-", "C": "Cr", "D": "Mn^2+"}),
        "option_values": ONE, "note": "lowest E0(red) -> its reduced form is the strongest reductant"},
    "m9dunp3y": {
        "formal": {"kind": "equation_system",
                   "knowns": {"Ec": K("0.8", "V"), "EQ": K("0.70", "V"), "s": K("0.06", "V"), "Ecell": K("0.4", "V"),
                              "C": K("0.01")},
                   "unknowns": {"pH": U("", "positive"), "pKb": U("", "positive")},
                   "equations": ["Ecell = Ec - (EQ - s*pH)", "pH = 7 - pKb/2 - log(C, 10)/2"], "target": "pKb",
                   "model": ["ASSUMPTION: E0(Q/QH2) = 0.70 V (standard value; the stem gives it only in an image)",
                             "quinhydrone anode: E = E0 - 0.06 pH; Ag+ 1 M cathode",
                             "NH4X salt of weak base/strong acid: pH = 7 - pKb/2 - log(C)/2"]},
        "explanation_value": "6", "note": "E0(quinhydrone) = 0.70 V assumed (image)"},
    "m9dv7asx": {
        "formal": {"kind": "equation_system",
                   "knowns": {"E0": K("1.33", "V"), "s": K("0.059", "V"), "Q": K("10**-6")},
                   "unknowns": {"pH": U("", "positive")},
                   "equations": ["0 = E0 - (s/6)*(log(Q, 10) + 14*pH)"], "target": "pH",
                   "model": ["Nernst: E = E0 - (0.059/6) log([Cr3+]^2/([Cr2O7 2-][H+]^14))"]},
        "explanation_value": "10", "note": "pH = 10.08"},
    "m9e5jawj": {
        "formal": {"kind": "equation_system",
                   "knowns": {"E0": K("0.46", "V"), "s": K("0.06", "V"), "Cu": K("1.0"), "Ag": K("0.1"),
                              "mV": K("1", "mV")},
                   "unknowns": {"E": U("V"), "x": U("")},
                   "equations": ["E = E0 - (s/2)*log(Cu/Ag**2, 10)", "E = x*mV"], "target": "x",
                   "model": ["ASSUMES inert electrodes during electrolysis: 1 F removes 0.5 mol Cu2+ (1.5 -> 1.0 M), "
                             "0.1 F removes 0.1 mol Ag+ (0.2 -> 0.1 M); with Cu/Ag electrodes concentrations would "
                             "not change (stem ambiguity)", "connection image assumed: Cu anode, Ag cathode"]},
        "explanation_value": "400", "note": "inert-electrode assumption"},
}

IMAGE_ONLY = {
    "m9fnus58": "structures in option images", "m6rp6klo": "structures in image",
    "m9fnutxl": "molecule and structures I-III in images", "m9fnuur4": "cyclic product of z only in image",
    "m9dunp1u": "molecules p-s in image", "m9ghxnq7": "reactants in option images",
    "m9ghxng2": "both statements in image", "m6v43dlc": "List-II structures are images",
    "m9enayd7": "compounds in statements are images", "m6qknb6k": "reaction sequences in images",
    "m6qqyn82": "reaction and products in images", "m6qr6qf7": "compounds A-D in images",
    "m6qvbxnc": "reaction sequence in image", "m6qvbxw4": "reaction sequence in image",
    "m6rp6k75": "List-I compounds A, B, D are images", "m6srn96u": "reaction sequence in image",
    "m6t9yk0p": "reaction sequence in image; no answer/explanation anywhere", "m6v43dtl": "conversion in image",
    "m9dr3n52": "options are structures (images)", "m9fnursf": "reaction sequence and options in images",
    "m9fnurvy": "reactions in option images", "m9f7uy3l": "List-I conversions in images",
    "m9ghxnin": "reaction and options in images", "m9gxgccn": "sequences in option images",
    "m9e5j9j4": "amines A and E are images", "m6w9ofqf": "graph values only in image (explanation invents them)",
}
