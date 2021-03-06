import random
from collections import defaultdict

import networkx as nx
import pandas as pd
from scipy import special
from statsmodels.stats import multitest

from .constants import *


def read_ppi_file(ppi_file: str = PPI_FILE, sep: str = SEPARATOR, ppi_columns=COLUMNS):
    """Reads in ppi file."""

    df_ppi = pd.read_csv(ppi_file, sep=sep, header=None)
    # assert that input columns are 3
    df_ppi.columns = ppi_columns

    df_ppi.Protein1 = df_ppi['Protein1'].str.lower()
    df_ppi.Protein2 = df_ppi['Protein2'].str.lower()

    df_interactions = df_ppi.replace("in-complex-with", +1)
    df_interactions = df_interactions.replace("controls-expression-of", -1)
    df_interactions = df_interactions.replace("controls-state-change-of", -1)
    # replace all other interaction expressions with 0
    # df_interactions.loc[(df_interactions.loc[COLUMNS[1]] != +1) & (df_interactions.loc[COLUMNS[1]] != -1)] = 0
    df_interactions[COLUMNS[1]].loc[(df_interactions[COLUMNS[1]] != +1)] = 0
    df_interactions[COLUMNS[1]].loc[(df_interactions[COLUMNS[1]] != -1)] = 0

    return df_interactions


def construct_graph_from_ppi(ppi_file: str = PPI_FILE, sep:str =SEPARATOR, ppi_columns=COLUMNS):
    """ Constructs a graph from a given PPI file.

    :param ppi_file: PPI file
    :param ppi_columns: column names for PPI file
    :return: NetworkX graph
    """

    df_interactions = read_ppi_file(ppi_file, sep, ppi_columns)

    graph = nx.DiGraph()

    for i in range(len(df_interactions)):
        prot1 = df_interactions.loc[i, COLUMNS[0]]
        prot2 = df_interactions.loc[i, COLUMNS[2]]
        interaction = df_interactions.loc[i, COLUMNS[1]]
        #G.add_node(prot1)
        #G.add_node(prot2)

        # edge attributes

        graph.add_edge(prot1, prot2, ** {RELATION: interaction})
        #G[prot1][prot2][RELATION] = interaction

    return graph


def filter_dgxp(dgxp_file: str = DGXP_FILE, sep: str = SEPARATOR, dgxp_columns=DGXPCOLUMNS,
                threshold: float = THRESHOLD):
    """
    Filters a DGXP file for fold-change significant genes.

    :param dgxp_file: DGXP file
    :param dgxp_columns: column names for DGXP file
    :param threshold: threshold for fold-change
    :return: DataFrame with filtered genes acc. to fold-change
    """
    # node attributes
    # TODO move to constants
    df_dgxp = pd.read_csv(dgxp_file, sep=sep, header=None, names=dgxp_columns)
    # select only necessary columns
    df_dgxp = df_dgxp[['Gene.symbol', 'logFC', 'adj.P.Val']].copy()
    # change column names accordingly
    # TODO: make dicionary from dgxp column names to those,, dicionary to constants
    df_dgxp.columns = ["gene", "fold-change", "p-value"]
    df_dgxp = df_dgxp.dropna()
    df_dgxp.gene = df_dgxp['gene'].str.lower()

    # filter dgxp

    # filter nodes with p-value < 0.05
    df_dgxp_pval_filtered = df_dgxp.loc[df_dgxp[DGXPCOLUMNS[2]] < PVALUE]

    # filter nodes with threshold (given by user)
    df_dgxp_thr_filtered = df_dgxp_pval_filtered.loc[abs(df_dgxp_pval_filtered[DGXPCOLUMNS[1]]) > threshold]

    # set fold change labels from float to +1 or -1
    df_dgxp_thr_filtered['fold-change'].loc[(df_dgxp_thr_filtered[DGXPCOLUMNS[1]] > 0)] = +1
    df_dgxp_thr_filtered['fold-change'].loc[(df_dgxp_thr_filtered[DGXPCOLUMNS[1]] < 0)] = -1

    # TODO: convert to dictionary
    return df_dgxp_thr_filtered


def set_node_label(graph, dgxp_file: str = DGXP_FILE, ppi_file: str = PPI_FILE, ppi_columns: str = COLUMNS,
                   sep=SEPARATOR, dgxp_columns=DGXPCOLUMNS,
                   threshold: float = THRESHOLD):
    """
    Sets the attribute LABEL of nodes according to the fold-change to +1 or -1.

    :param dgxp_file:
    :param sep:
    :param threshold:
    :param dgxp_columns:
    :param graph: NetworkX graph
    """
    df_ppi = read_ppi_file(ppi_file, sep, ppi_columns)

    df = filter_dgxp(dgxp_file, sep, dgxp_columns, threshold)

    for prot1 in df_ppi[COLUMNS[0]]:

        if prot1 in list(df['gene']):
            index = df[df.gene == prot1.index[0]]
            graph.nodes[prot1][LABEL] = df_ppi.loc[index, ['fold-change']]
            # print(df_dgxp.loc[index, 'fold-change'])
            print(f"Label for {prot1} is now {df.loc[index, 'fold-change']}")

    # nodes = df.loc[DGXPCOLUMNS[0]]
    # fold_changes = df.loc[DGXPCOLUMNS[1]]
    # node_label_dic = {node: label for (node, label) in zip(nodes, fold_changes)}

    # nx.set_node_attributes(graph, node_label_dic, name=LABEL)

    for node in graph.nodes():
        if graph[node][LABEL] is None:
            raise KeyError(f"The node {node} has not been labeled.")


def construct_graph(ppi_file: str = PPI_FILE, dgxp_file: str = DGXP_FILE, sep=SEPARATOR, ppi_columns=COLUMNS,
                    dgxp_columns=DGXPCOLUMNS, threshold: float = THRESHOLD):
    """
    Constructs a NetworkX graph.
        :param ppi_file: tsv file about PPI
        :param dgxp_file: tsv file about differential gene expression
        :param sep:
        :param ppi_columns: list of columns names of PPI file
        :param dgxp_columns: list of column names of DGXP file
        :param threshold:
        :return: NetworkX graph
    """
    # construct the graph
    graph = construct_graph_from_ppi(ppi_file, sep, ppi_columns)

    # filter relevant fold change nodes
    filtered_dgxp_file = filter_dgxp(dgxp_file, sep, dgxp_columns, threshold)

    # label nodes as up- or -downregulated
    set_node_label(graph, dgxp_file, sep, dgxp_columns, threshold)

    return graph





def random_node_labels(graph):
    """
    Randomly assigns labels of [-1,0,1] to nodes in a graph
    Labels:
    -1 : Downregulated
    0 : No change
    +1 : Upregulated

    Input:
        - graph : the graph consisting of protein nodes

    Output:
        - prints list of nodes with associated attribute label
    """
    for node in graph.nodes():
        random_label = random.randint(-1, 1)
        graph.nodes[node][LABEL] = random_label
    print(graph.nodes.data())




def shortest_path(graph, source):
    """
    Caclulates the shortest path between two nodes.

    Input:
        - graph : NetworkX graph
        - source : upstream source node


    Output:
        - dictionary of shortest path nodes between source node and all other nodes in graph
    """
    # for target in graph.nodes():
    shortest_paths = nx.shortest_path(graph, source)
    return shortest_paths





def count_concordance(graph: nx.DiGraph, source):
    """
    Check if node labels of source and target node are the same

    Input:
        - graph: NetworkX graph
        - source: source upstream node

    Output:
        - list of concordant and non-concordant nodes for the source node
    """
    same_label = False

    nodes_dic = defaultdict(list)

    for target, path_nodes in shortest_path(graph, source).items():

        # check if node labels of source and target are the same
        if graph.nodes[source][LABEL] * graph.nodes[target][LABEL] is 1:
            same_label = True

        # multiply the edge labels
        edge_label = [
            graph[path_nodes[i]][path_nodes[i + 1]][RELATION] * graph[path_nodes[i]][path_nodes[i + 1]]['relation']
            for i in range(len(path_nodes) - 1)]

        # edge_label = 1
        # for i in range(len(path_nodes)-1):
        #    temp_edge_label = G[path_nodes[i]][path_nodes[i+1]]['relation']
        #    edge_label *= temp_edge_label

        # concordant node
        if same_label is True and edge_label is +1:
            graph.nodes[target][CONCORDANCE] = +1
            nodes_dic[CONCORDANT].append(target)

        # non-concordant node
        if same_label is False and edge_label is -1:
            graph.nodes[target][CONCORDANCE] = -1
            nodes_dic[NONCONCORDANT].append(target)

        # no change node
        if graph.nodes[source][LABEL] is 0 and graph.nodes[target][LABEL] is 0:
            nodes_dic[NOCHANGE].append(target)

    return nodes_dic





def nodes_dictionary(graph):
    """
    Returns a dictionary of the nodes of the graph with their according
         - shortest path nodes
         - concordant nodes
         - non-concordant nodes
         - no change nodes

    Input:
        - graph

    Output:
        - dictionary of nodes
    """
    dic = {}
    for node in graph.nodes():
        dic[node] = {}

        # concordant, non-concordant and no change nodes
        dic[node] = count_concordance(graph, node)

        # shortest path nodes
        dic[node][SHORTESTPATH] = list(shortest_path(graph, node).keys())

    return dic





def calculate_concordance(graph, p: float = PROBABILITY):
    """
    Calculates the concordance for an upstream node with its downstream nodes
    Probability of getting at least the number of state changes consistent
    with the direction
    Input:
        - graph
        - p : probability of achieving a result

    Output:
        - dictionary of p-values and corrected p-values for concordance
    """
    concordance_dic = {}

    assert 0 <= p <= 1, "p must be within [0,1]"

    for hyp_node in graph.nodes():
        if hyp_node not in graph.nodes():
            raise ValueError(f"The node {hyp_node} is not in the graph.")
        # n is number of trials
        n = len(shortest_path(graph, hyp_node).keys())
        # k is number of successful predictions
        k = len(count_concordance(graph, hyp_node)[CONCORDANT])
    # TODO: substract no change from n
        bin_coeff = special.binom(n, k)
        concordance = bin_coeff * (p ** k) * (1 - p) ** (n - k)
        concordance_dic[hyp_node] = {}
        concordance_dic[hyp_node][PVAL] = concordance

    # correction for multiple testing
    reject, pvals_corrected = multitest.multipletests(concordance_dic.values(), alpha=0.05, method='bonferroni')
    for node, pval in zip(graph.nodes(), pvals_corrected):
        concordance_dic[node][PVALCORRECTED] = pval

    return concordance_dic



def write_concordance_csv(graph, csv_output: str = OUTPUT_FILE, p: float = PROBABILITY):
    """
    Writes the values for nodes, concordant_nodes, non_concordant_nodes, no_change_nodes, p_val, p_val_corrected to a csv file

    Input:
    - graph
    - csv_output : path for output file
    - p: probability


    """
    rows = []
    for node in graph.nodes():
        node_dict = {
            NODE: node,
            CONCORDANT: len(count_concordance(graph, node)[CONCORDANT]),
            NONCONCORDANT: len(count_concordance(graph, node)[NONCONCORDANT]),
            NOCHANGE: len(count_concordance(graph, node)[NOCHANGE]),
            PVAL: calculate_concordance(graph)[node][PVAL],
            PVALCORRECTED: calculate_concordance(graph, p)[node][PVALCORRECTED]
        }

        rows.append(node_dict)

    df_ = pd.DataFrame(rows)
    # TODO change output
    df_.to_csv(csv_output)


"""

if __name__ == '__main__':

    file = "/Users/sophiakrix/git/MechanismEnrichmentLab/example.txt"
    # Create parser
    #parser = argparse.ArgumentParser(description='csv file with Protein1, interaction and Protein2 information')

    # Execute the parse_args() method
    #args = parser.parse_args()
    #file = args.Path

    if not os.path.exists(file):
        raise IOError('The path specified does not exist')

    #file = sys.argv[1]

    # TODO: csv_output argument

    g = construct_graph(file)

    print(f"The concordance of each HYP node of the graph is as follows: ")

    write_concordance_csv(g,csv_output)
"""
