"""Feature panels and biological constants from the precisionFDA challenge.

Contains original notebook-derived panels plus known MSI pathway markers
used for biological validation of agent-selected biomarkers.
"""

# ---------------------------------------------------------------------------
# Original Feature Panels (from precisionFDA notebooks)
# ---------------------------------------------------------------------------

MSI_PROTEOMICS_PANEL: list[str] = [
    "TAP1", "LCP1", "PTPN6", "CASK", "ICAM1", "ITGB2", "CKB", "LAP3",
    "PTPRC", "HSDL2", "WARS", "IFI35", "TYMP", "TAPBP", "ERMP1", "ANP32E",
    "ROCK2", "CNDP2", "RFTN1", "GBP1", "NCF2", "YARS2", "RPL3", "ENO1",
    "SNX12", "ARL3",
]

MSI_RNASEQ_PANEL: list[str] = [
    "EPDR1", "APOL3", "POU5F1B", "CFTR", "CIITA", "MAX", "PRSS23",
    "FABP6", "GABRP", "SLC19A3", "RAMP1", "AREG", "EREG", "TNNC2",
    "ANKRD27", "PLCL2", "TFCP2L1", "LAG3", "GRM8", "BEX2", "DEFB1",
    "IRF1", "CCL4", "SLC51B", "GBP4", "HPSE",
]

GENDER_PROTEOMICS_PANEL: list[str] = [
    "DDX3Y", "EIF1AY", "KDM5D", "RPS4Y1", "USP9Y", "UTY", "ZFY",
    "KDM5C", "XIST",
]

GENDER_RNASEQ_PANEL: list[str] = [
    "DDX3Y", "EIF1AY", "KDM5D", "RPS4Y1", "USP9Y", "UTY", "ZFY",
    "XIST", "TSIX",
]

# Top RF importance scores from original notebooks
TOP_RF_IMPORTANCE: dict[str, float] = {
    "S100A14": 0.318,
    "ROCK2": 0.076,
    "FHDC1": 0.071,
    "PGM2": 0.053,
    "GAR1": 0.042,
}

# ---------------------------------------------------------------------------
# Known MSI Pathway Markers (for biological validation)
# ---------------------------------------------------------------------------

KNOWN_MSI_PATHWAY_MARKERS: dict[str, list[str]] = {
    "immune_infiltration": ["PTPRC", "ITGB2", "LCP1", "NCF2"],
    "interferon_response": ["GBP1", "GBP4", "IRF1", "IFI35", "WARS"],
    "antigen_presentation": ["TAP1", "TAPBP", "LAG3"],
    "mismatch_repair_adjacent": ["CIITA", "TYMP"],
}

# All known MSI markers flattened
ALL_KNOWN_MSI_MARKERS: set[str] = {
    gene
    for genes in KNOWN_MSI_PATHWAY_MARKERS.values()
    for gene in genes
}

# ---------------------------------------------------------------------------
# Y-Chromosome Genes (for MNAR classification in female samples)
# ---------------------------------------------------------------------------

Y_CHROMOSOME_GENES: list[str] = [
    "DDX3Y", "EIF1AY", "KDM5D", "RPS4Y1", "USP9Y", "UTY", "ZFY",
]

# ---------------------------------------------------------------------------
# Analysis Constants
# ---------------------------------------------------------------------------

DEFAULT_AVAILABILITY_THRESHOLD: float = 0.9
DEFAULT_N_TOP_FEATURES: int = 30
DEFAULT_SUBSAMPLING_ITERATIONS: int = 100
DEFAULT_GENE_SAMPLING_FRACTION: float = 0.8
