from enum import Enum


class BioLinkVocabulary(Enum):
    category = "biolink:category"  # this is a node property, not a class
    Publication = "biolink:Publication"
    Disease = "biolink:Disease"
    Gene = "biolink:Gene"
    Genotype = "biolink:Genotype"
    NamedThing = "biolink:NamedThing"
    PopulationOfIndividualOrganisms = "biolink:PopulationOfIndividualOrganisms"
    SequenceVariant = "biolink:SequenceVariant"  # synonym for allele
    InformationContentEntity = "biolink:InformationContentEntity"
    Zygosity = "biolink:Zygosity"
    PhenotypicFeature = "biolink:PhenotypicFeature"
    Publications = "biolink:Publications"
    BiologicalSex = "biolink:BiologicalSex"
    OrganismTaxon = "biolink:OrganismTaxon"
    MolecularEntity = "biolink:MolecularEntity"
    Case = "biolink:Case"
    OntologyClass = "biolink:OntologyClass"
    GeneFamily = "biolink:GeneFamily"
