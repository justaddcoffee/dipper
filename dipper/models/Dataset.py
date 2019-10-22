"""
Produces metadata about ingested data
"""

import logging
import hashlib
from datetime import datetime
from rdflib import Literal, XSD
from dipper.graph.RDFGraph import RDFGraph
from dipper.graph.StreamedGraph import StreamedGraph
from dipper.models.Model import Model

__author__ = 'nlw'

LOG = logging.getLogger(__name__)


class Dataset:
    """
     This class produces metadata about a dataset that is compliant with the
     HCLS dataset specification:
     https://www.w3.org/TR/2015/NOTE-hcls-dataset-20150514/#s4_4

     Summary level: The summary level provides a description of a dataset that is
     independent of a specific version or format. (e.g. the Monarch ingest of CTD)
     CURIE for this is something like MonarchData:[SOURCE IDENTIFIER]

     Version level: The version level captures version-specific characteristics of a
     dataset. (e.g. the 01-02-2018 ingest of CTD)
     CURIE for this is something like MonarchData:[SOURCE IDENTIFIER_INGESTTIMESTAMP]

     Distribution level: The distribution level captures metadata about a specific form
     and version of a dataset (e.g. turtle file for 01-02-2018 ingest of CTD). There is
     a [distribution level resource] for each different downloadable file we emit,
     i.e. one for the TTL file, one for the ntriples file, etc.
     CURIE for this is like MonarchData:[SOURCE IDENTIFIER_INGESTTIMESTAMP].ttl
     or
     MonarchData:[SOURCE IDENTIFIER_INGESTTIMESTAMP].nt
     or
     MonarchData:[SOURCE IDENTIFIER_INGESTTIMESTAMP].[whatever file format]

     We write out at least the following triples:

     SUMMARY LEVEL TRIPLES:
     [summary level resource] - rdf:type -> dctypes:Dataset
     [summary level resource] - dct:title -> title (literal)
     [summary level resource] - dct:description -> description (literal)
                                                (use docstring from Source class)
     [summary level resource] - dcterms:source -> [source web page, e.g. omim.org]
     [summary level resource] - schemaorg:logo -> [source logo IRI]
     [summary level resource] - dct:publisher -> monarchinitiative.org
        n.b: about summary level resource triples:
        -- HCLS spec says we "should" link to our logo and web page, but I'm not,
        because it would confuse the issue of whether we are pointing to our logo/page
        or the logo/page of the data source for this ingest. Same below for
        [version level resource] and [distibution level resource] - I'm not linking to
        our page/logo down there either.
        - spec says we "should" include summary level triples describing Update
        frequency and SPARQL endpoint but I'm omitting this for now, because these are
        not clearly defined at the moment

     VERSION LEVEL TRIPLES:
     [version level resource] - rdf:type -> dctypes:Dataset
     [version level resource] - dct:title -> version title (literal)
     [version level resource] - dct:description -> version description (literal)
     [version level resource] - dct:created -> ingest timestamp [ISO 8601 compliant]
     [version level resource] - pav:version -> ingest timestamp (same one above)
     [version level resource] - dct:creator	-> monarchinitiative.org
     [version level resource] - dct:publisher -> monarchinitiative.org
     [version level resource] - dct:isVersionOf -> [summary level resource]
     [version level resource] - dcterms:source -> [source file 1 IRI]
     [version level resource] - dcterms:source -> [source file 2 IRI]
     ...

     [source file 1 IRI] - pav:retrievedOn -> [download date timestamp]
     [source file 2 IRI] - pav:version -> [source version (if set, optional)]
     [source file 2 IRI] - pav:retrievedOn -> [download date timestamp]
     [source file 2 IRI] - pav:version -> [source version (if set, optional)]
     ...

     [version level resource] - pav:createdWith -> [Dipper github URI]
     [version level resource] - void:dataset -> [distribution level resource]

     [version level resource] - cito:citesAsAuthoriy -> [citation id 1]
     [version level resource] - cito:citesAsAuthoriy -> [citation id 2]
     [version level resource] - cito:citesAsAuthoriy -> [citation id 3]

        n.b: about version level resource triples:
        - spec says we "should" include Date of issue/dct:issued triple, but I'm not
        because it is redundant with this triple above:
        [version level resource] - dct:created -> time stamp
        and would introduce ambiguity and confusion if the two disagree. Same below
        for [distribution level resource] - dct:created -> tgiime stamp below
        Also omitting:
          - triples linking to our logo and page, see above.
          - License/dct:license triple, because we will make this triple via the
            [distribution level resource] below
          - Language/dct:language triple b/c it seems superfluous. Same below for
            [distribution level resource] - no language triple.
        - [version level resource] - pav:version triple is also a bit redundant
        with the pav:version triple below, but the spec requires both these triples
        - I'm omitting the [version level resource] -> pav:previousVersion because
        Dipper doesn't know this info for certain at run time. Same below for
        [distribution level resource] - pav:previousVersion.


     DISTRIBUTION LEVEL TRIPLES:
     [distribution level resource] - rdf:type -> dctypes:Dataset
     [distribution level resource] - rdf:type -> dcat:Distribution
     [distribution level resource] - dct:title -> distribution title (literal)
     [distribution level resource] - dct:description -> distribution description (lit.)
     [distribution level resource] - dct:created -> ingest timestamp[ISO 8601 compliant]
     [distribution level resource] - pav:version -> ingest timestamp (same as above)
     [distribution level resource] - dct:creator -> monarchinitiative.org
     [distribution level resource] - dct:publisher -> monarchinitiative.org
     [distribution level resource] - dct:license -> [license info, if available
                    otherwise indicate unknown]
     [distribution level resource] - dcterms:rights -> [data rights IRI]
     [distribution level resource] - pav:createdWith -> [Dipper github URI]
     [distribution level resource] - dct:format -> [IRI of ttl|nt|whatever spec]
     [distribution level resource] - dct:downloadURL -> [ttl|nt URI]
     [distribution level resource] - void:triples -> [triples count (literal)]
     [distribution level resource] - void:entities -> [entities count (literal)]
     [distribution level resource] - void:distinctSubjects -> [subject count (literal)]
     [distribution level resource] - void:distinctObjects -> [object count (literal)]
     [distribution level resource] - void:properties -> [properties count (literal)]
     ...

        n.b: about distribution level resource triples:
        - omitting Vocabularies used/void:vocabulary and Standards
        used/dct:conformTo triples, because they are described in the ttl file
        - also omitting Example identifier/idot:exampleIdentifier and
        Example resource/void:exampleResource, because we don't really have one
        canonical example of either - they're all very different.
        - [distribution level resource] - dct:created should have the exact same
        time stamp as this triple above:
        [version level resource] - dct:created -> time stamp
        - this [distribution level resource] - pav:version triple should have the
        same object as [version level resource] - pav:version triple above
        - Data source provenance/dct:source triples are above in the
        [version level resource]
        - omitting Byte size/dct:byteSize, RDF File URL/void:dataDump, and
        Linkset/void:subset triples because they probably aren't necessary for MI right
        now
        - these triples "should" be emitted, but we will do this in a later iteration:
        # of classes	void:classPartition	IRI
        # of literals	void:classPartition	IRI
        # of RDF graphs	void:classPartition	IRI

     Note: Do not use blank nodes in the dataset graph. This dataset graph is added to
     the main Dipper graph in Source.write() like so

        $ mainGraph = mainGraph + datasetGraph

     which apparently in theory could lead to blank node ID collisions between the two
     graphs.

     Note also that this implementation currently does not support producing metadata
     for StreamedGraph graphs (see dipper/graph/StreamedGraph.py). StreamedGraph is
     currently not being used for any ingests, so this isn't a problem. There was
     talk of using StreamedGraph for a rewrite/refactor of the Clinvar ingest, which
     would probably require adding support here for StreamedGraph's.
    """

    def __init__(
            self,
            identifier,
            data_release_version,
            ingest_name,
            ingest_title,
            ingest_url,
            ingest_logo=None,
            ingest_description=None,
            license_url=None,
            data_rights=None,
            graph_type='rdf_graph',     # rdf_graph, streamed_graph
            file_handle=None,
            distribution_type='ttl',
            dataset_curie_prefix='MonarchArchive'
    ):

        if graph_type is None:
            self.graph = RDFGraph(None,
                                  ":".join([dataset_curie_prefix, identifier]))
        elif graph_type == 'streamed_graph':
            self.graph = StreamedGraph(True,
                                       ":".join([dataset_curie_prefix, identifier]),
                                       file_handle=file_handle)
        elif graph_type == 'rdf_graph':
            self.graph = RDFGraph(True,
                                  ':'.join([dataset_curie_prefix, identifier]))

        if data_release_version is not None:
            self.data_release_version = data_release_version
        else:
            self.data_release_version = datetime.today().strftime("%Y%m%d")

        self.model = Model(self.graph)
        self.globaltt = self.graph.globaltt
        self.globaltcid = self.graph.globaltcid
        self.curie_map = self.graph.curie_map
        self.identifier = ':'.join([dataset_curie_prefix, identifier])
        self.citation = set()

        self.ingest_name = ingest_name
        self.ingest_title = ingest_title
        if self.ingest_title is None:
            self.ingest_title = ":".join([dataset_curie_prefix, identifier])

        self.ingest_url = ingest_url
        self.ingest_logo = self.curie_map.get('MonarchLogoRepo') + ingest_logo
        self.ingest_description = ingest_description

        self.date_issued = None

        self.license_url = license_url
        self.data_rights = data_rights
        self.distribution_type = distribution_type

        # set HCLS resource CURIEs
        self.summary_level_curie = ':'.join([dataset_curie_prefix, '#' + identifier])
        self.version_level_curie = \
            dataset_curie_prefix + ':' + \
            self.data_release_version + \
            '/#' + identifier
        self.distribution_level_turtle_curie = \
            dataset_curie_prefix + ':' + \
            self.data_release_version + \
            '/rdf/' + \
            identifier + "." + self.distribution_type

        # The following might seem a little odd, but we need to set downloadURLs this
        # way in order for them to point to where they will end up in archive.MI.org as
        # of Sept 2019. URL is:
        #  https://archive.MI.org/[release version]/[dist type]/[source].[dist type]
        self.download_url = \
            self.curie_map.get("MonarchArchive") + self.data_release_version + \
            "/rdf/" + self.ingest_name + "." + self.distribution_type

        self._set_summary_level_triples()
        self._set_version_level_triples()
        self._set_distribution_level_triples()

    def _set_summary_level_triples(self):
        self.model.addType(self.summary_level_curie, self.globaltt['Dataset'])
        self.graph.addTriple(self.summary_level_curie,
                             self.globaltt['title'],
                             self.ingest_title,
                             True)
        self.model.addTriple(self.summary_level_curie, self.globaltt['Publisher'],
                             self.curie_map.get(""))
        self.model.addTriple(self.summary_level_curie,
                             "schemaorg:logo",
                             self.ingest_logo)
        self.graph.addTriple(self.summary_level_curie, self.globaltt['identifier'],
                             self.summary_level_curie)
        if self.ingest_url is not None:
            self.graph.addTriple(self.summary_level_curie,
                                 self.globaltt["Source (dct)"],
                                 self.ingest_url)
        if self.ingest_description is not None:
            self.model.addDescription(self.summary_level_curie, self.ingest_description)

    def _set_version_level_triples(self):
        self.model.addType(self.version_level_curie, self.globaltt['Dataset'])
        self.graph.addTriple(self.version_level_curie, self.globaltt['title'],
                             self.ingest_title +
                             " Monarch version " +
                             self.data_release_version,
                             True)
        if self.ingest_description is not None:
            self.model.addDescription(self.version_level_curie,
                                      self.ingest_description)
        self.graph.addTriple(self.version_level_curie, self.globaltt['created'],
                             Literal(self.data_release_version, datatype=XSD.date))
        self.graph.addTriple(self.version_level_curie, self.globaltt['version'],
                             Literal(self.data_release_version, datatype=XSD.date))
        self.graph.addTriple(self.version_level_curie, self.globaltt['creator'],
                             self.curie_map.get(""))  # eval's to MI.org
        self.graph.addTriple(self.version_level_curie, self.globaltt['Publisher'],
                             self.curie_map.get(""))  # eval's to MI.org
        self.graph.addTriple(self.version_level_curie, self.globaltt['isVersionOf'],
                             self.summary_level_curie, object_is_literal=False)
        self.graph.addTriple(self.version_level_curie,
                             self.globaltt['distribution'],
                             self.distribution_level_turtle_curie,
                             object_is_literal=False)

    def _set_distribution_level_triples(self):
        self.model.addType(self.distribution_level_turtle_curie,
                           self.globaltt['Dataset'])
        self.model.addType(self.distribution_level_turtle_curie,
                           self.globaltt['distribution'])
        self.graph.addTriple(self.distribution_level_turtle_curie,
                             self.globaltt['title'],
                             self.ingest_title +
                             " distribution " +
                             self.distribution_type,
                             True)
        if self.ingest_description is not None:
            self.model.addDescription(self.distribution_level_turtle_curie,
                                      self.ingest_description)
        self.graph.addTriple(self.distribution_level_turtle_curie,
                             self.globaltt['version'],
                             Literal(self.data_release_version, datatype=XSD.date))
        self.graph.addTriple(self.distribution_level_turtle_curie,
                             self.globaltt['created'],
                             Literal(self.data_release_version, datatype=XSD.date))
        self.graph.addTriple(self.distribution_level_turtle_curie,
                             self.globaltt['creator'],
                             self.curie_map.get(""))  # eval's to MI.org
        self.graph.addTriple(self.distribution_level_turtle_curie,
                             self.globaltt['Publisher'],
                             self.curie_map.get(""))  # eval's to MI.org
        self.graph.addTriple(self.distribution_level_turtle_curie,
                             self.globaltt['created_with'],
                             "https://github.com/monarch-initiative/dipper")
        self.graph.addTriple(self.distribution_level_turtle_curie,
                             self.globaltt['format'],
                             "https://www.w3.org/TR/turtle/")
        self.graph.addTriple(self.distribution_level_turtle_curie,
                             self.globaltt['downloadURL'],
                             self.download_url)
        if self.license_url is None:
            self.graph.addTriple(self.distribution_level_turtle_curie,
                                 self.globaltt['license'],
                                 'https://project-open-data.cio.gov/unknown-license/')
        else:
            self.graph.addTriple(self.distribution_level_turtle_curie,
                                 self.globaltt['license'],
                                 self.license_url)

        if self.data_rights is not None:
            self.graph.addTriple(self.distribution_level_turtle_curie,
                                 self.globaltt['rights'],
                                 self.data_rights)

        self._declare_as_ontology()

    def set_ingest_source_file_version_num(self, file_iri, version):
        """
        This method sets the version of a remote file or resource that is used in the
        ingest. It writes this triple:

        file_iri - 'pav:version' -> version

        Version is an untyped literal

        Note: if your version is a date or timestamp, use
        set_ingest_source_file_version_date()
        instead

        :param file_iri: a remote file or resource used in ingest
        :param version: a number or string (e.g. v1.2.3) that the source (OMIM, CTD)
        uses to refer to this version of the file/resource used during the ingest
        :return: None
        """
        self.graph.addTriple(file_iri, self.globaltt['version'], version,
                             object_is_literal=True)

    def set_ingest_source_file_version_date(self, file_iri, date, datatype=XSD.date):
        """
        This method sets the version that the source (OMIM, CTD, whatever) uses to
        refer to this version of the remote file/resource that was used in the ingest

        It writes this triple:

        file_iri - 'pav:version' -> date or timestamp

        Version is added as a literal of datatype XSD date

        Note: if file_iri was retrieved using get_files(), then the following triple
        was created and you might not need this method:

        file_iri - 'pav:retrievedOn' -> download date

        :param file_iri: a remote file or resource used in ingest
        :param date: a date in YYYYMMDD format that the source (OMIM, CTD). You can
        add timestamp as a version by using a different datatype (below)
        :param datatype: an XSD literal datatype, default is XSD.date
        uses to refer to this version of the file/resource used during the ingest
        :return: None
        """
        self.graph.addTriple(file_iri, self.globaltt['version'], date,
                             object_is_literal=True, literal_type=datatype)

    def set_ingest_source_file_version_retrieved_on(self,
                                                    file_iri,
                                                    date,
                                                    datatype=XSD.date):
        """
        This method sets the date on which a remote file/resource (from OMIM, CTD, etc)
        was retrieved.

        It writes this triple:

        file_iri - 'pav:retrievedOn' -> date or timestamp

        Version is added as a literal of datatype XSD date by default

        Note: if file_iri was retrieved using get_files(), then the following triple
        was created and you might not need this method:

        file_iri - 'pav:retrievedOn' -> download date

        :param file_iri: a remote file or resource used in ingest
        :param date: a date in YYYYMMDD format that the source (OMIM, CTD). You can
        add timestamp as a version by using a different datatype (below)
        :param datatype: an XSD literal datatype, default is XSD.date
        uses to refer to this version of the file/resource used during the ingest
        :return: None
        """
        self.graph.addTriple(file_iri, self.globaltt['retrieved_on'], date,
                             object_is_literal=True, literal_type=datatype)

    def set_ingest_source(self, url,
                          predicate=None,
                          is_object_literal=False):
        """
        This method writes a triple to the dataset graph indicating that the ingest
        used a file or resource at [url] during the ingest.

        Triple emitted is version_level_curie dcterms:source [url]

        This triple is likely to be redundant if Source.get_files() is used to retrieve
        the remote files/resources, since this triple should also be emitted
        as files/resources are being retrieved. This method is provided as a convenience
        method for sources that do their own downloading of files.

        :param url: a remote resource used as a source during ingest
        :param predicate: the predicate to use for the triple ["dcterms:source"]
                from spec (https://www.w3.org/TR/2015/NOTE-hcls-dataset-20150514/)
                "Use dct:source when the source dataset was used in whole or in part.
                Use pav:retrievedFrom when the source dataset was used in whole and was
                not modified from its original distribution. Use prov:wasDerivedFrom
                when the source dataset was in whole or in part and was modified from
                its original distribution."
        :return: None
        """
        if predicate is None:
            predicate = self.globaltt["Source (dct)"]
        self.graph.addTriple(
            self.version_level_curie, predicate, url,
            object_is_literal=is_object_literal)

    def get_graph(self):
        """
        This method returns the dataset graph
        :param
        :return: dataset graph
        """
        return self.graph

    def get_license(self):
        """
        This method returns the license info
        :param
        :return: license info
        """
        return self.license_url

    def set_citation(self, citation_id):
        """
        This method adds [citaton_id] argument to the set of citations, and also
        adds a triple indicating that version level cito:citesAsAuthority [citation_id]
        :param: citation_id
        :return: none
        """
        self.citation.add(citation_id)
        self.graph.addTriple(
            self.version_level_curie, self.globaltt['citesAsAuthority'], citation_id)

    def _declare_as_ontology(self, version_info=None):
        """
        Declare the distribution level IRI as an ontology, and also make triple
        distribution level IRI - version_iri -> version level IRI

        TEC: I am not convinced dipper reformatting external data as RDF triples
        makes an OWL ontology (nor that it should be considered a goal).

        Proper ontologies are built by ontologists. Dipper reformats data
        and annotates/decorates it with a minimal set of carefully arranged
        terms drawn from from multiple proper ontologies.
        Which allows the whole (dipper's RDF triples and parent ontologies)
        to function as a single ontology we can reason over when combined
        in a store such as SciGraph.

        Including more than the minimal ontological terms in dipper's RDF
        output constitutes a liability as it allows greater divergence
        between dipper artifacts and the proper ontologies.

        :param version_info: a string describing version info for the ontology
        :return:

        """
        model = Model(self.graph)
        model.addOntologyDeclaration(self.summary_level_curie)
        model.addOWLVersionIRI(self.summary_level_curie,
                               self.version_level_curie)
        if version_info is not None:
            model.addOWLVersionInfo(self.distribution_level_turtle_curie,
                                    version_info)

    @staticmethod
    def make_id(long_string, prefix='MONARCH'):
        """
        A method to create DETERMINISTIC identifiers
        based on a string's digest. currently implemented with sha1
        Duplicated from Source.py to avoid circular imports.
        :param long_string: string to use to generate identifier
        :param prefix: prefix to prepend to identifier [Monarch]
        :return: a Monarch identifier
        """
        return ':'.join((prefix, Dataset.hash_id(long_string)))

    @staticmethod
    def hash_id(word):  # same as graph/GraphUtils.digest_id(wordage)
        """
        Given a string, make a hash
        Duplicated from Source.py.

        :param word: str string to be hashed
        :return: hash of id
        """
        return 'b' + hashlib.sha1(word.encode('utf-8')).hexdigest()[1:20]
