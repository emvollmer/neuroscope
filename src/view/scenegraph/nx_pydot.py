# pylint: skip-file
"""
*****
Pydot
*****

Import and export NetworkX graphs in Graphviz dot format using pydot.

Either this module or nx_agraph can be used to interface with graphviz.

See Also
--------
pydot:         https://github.com/erocarrera/pydot
Graphviz:      https://www.graphviz.org
DOT Language:  http://www.graphviz.org/doc/info/lang.html
"""
# Author: Aric Hagberg (aric.hagberg@gmail.com)

#    Copyright (C) 2004-2019 by
#    Aric Hagberg <hagberg@lanl.gov>
#    Dan Schult <dschult@colgate.edu>
#    Pieter Swart <swart@lanl.gov>
#    Cecil Curry <leycec@gmail.com>
#    All rights reserved.
#    BSD license.
import re
from locale import getpreferredencoding
from networkx.utils import open_file
import networkx as nx

__all__ = ['write_dot', 'read_dot', 'graphviz_layout', 'pydot_layout',
           'to_pydot', 'from_pydot']

# 2.x/3.x compatibility
try:
    basestring
except NameError:
    basestring = str
    unicode = str


@open_file(1, mode='w')
def write_dot(G, path):
    """Write NetworkX graph G to Graphviz dot format on path.

    Path can be a string or a file handle.
    """
    P = to_pydot(G)
    path.write(P.to_string())
    return


@open_file(0, mode='r')
def read_dot(path):
    """Returns a NetworkX :class:`MultiGraph` or :class:`MultiDiGraph` from the
    dot file with the passed path.

    If this file contains multiple graphs, only the first such graph is
    returned. All graphs _except_ the first are silently ignored.

    Parameters
    ----------
    path : str or file
        Filename or file handle.

    Returns
    -------
    G : MultiGraph or MultiDiGraph
        A :class:`MultiGraph` or :class:`MultiDiGraph`.

    Notes
    -----
    Use `G = nx.Graph(read_dot(path))` to return a :class:`Graph` instead of a
    :class:`MultiGraph`.
    """
    pydot = _import_pydot()
    data = path.read()

    # List of one or more "pydot.Dot" instances deserialized from this file.
    P_list = pydot.graph_from_dot_data(data)

    # Convert only the first such instance into a NetworkX graph.
    return from_pydot(P_list[0])


def from_pydot(P):
    """Returns a NetworkX graph from a Pydot graph.

    Parameters
    ----------
    P : Pydot graph
      A graph created with Pydot

    Returns
    -------
    G : NetworkX multigraph
        A MultiGraph or MultiDiGraph.

    Examples
    --------
    >>> K5 = nx.complete_graph(5)
    >>> A = nx.nx_pydot.to_pydot(K5)
    >>> G = nx.nx_pydot.from_pydot(A) # return MultiGraph

    # make a Graph instead of MultiGraph
    >>> G = nx.Graph(nx.nx_pydot.from_pydot(A))

    """
    if P.get_strict(None):  # pydot bug: get_strict() shouldn't take argument
        multiedges = False
    else:
        multiedges = True

    if P.get_type() == 'graph':  # undirected
        if multiedges:
            N = nx.MultiGraph()
        else:
            N = nx.Graph()
    else:
        if multiedges:
            N = nx.MultiDiGraph()
        else:
            N = nx.DiGraph()

    # assign defaults
    name = P.get_name().strip('"')
    if name != '':
        N.name = name

    # add nodes, attributes to N.node_attr
    for p in P.get_node_list():
        n = p.get_name().strip('"')
        if n in ('node', 'graph', 'edge'):
            continue
        N.add_node(n, **p.get_attributes())

    # add edges
    for e in P.get_edge_list():
        u = e.get_source()
        v = e.get_destination()
        attr = e.get_attributes()
        s = []
        d = []

        if isinstance(u, basestring):
            s.append(u.strip('"'))
        else:
            for unodes in u['nodes']:
                s.append(unodes.strip('"'))

        if isinstance(v, basestring):
            d.append(v.strip('"'))
        else:
            for vnodes in v['nodes']:
                d.append(vnodes.strip('"'))

        for source_node in s:
            for destination_node in d:
                N.add_edge(source_node, destination_node, **attr)

    # add default attributes for graph, nodes, edges
    pattr = P.get_attributes()
    if pattr:
        N.graph['graph'] = pattr
    try:
        N.graph['node'] = P.get_node_defaults()[0]
    except:  # IndexError,TypeError:
        pass  # N.graph['node']={}
    try:
        N.graph['edge'] = P.get_edge_defaults()[0]
    except:  # IndexError,TypeError:
        pass  # N.graph['edge']={}
    return N


def to_pydot(N):
    """Returns a pydot graph from a NetworkX graph N.

    Parameters
    ----------
    N : NetworkX graph
      A graph created with NetworkX

    Examples
    --------
    >>> K5 = nx.complete_graph(5)
    >>> P = nx.nx_pydot.to_pydot(K5)

    Notes
    -----

    """
    pydot = _import_pydot()

    # set Graphviz graph type
    if N.is_directed():
        graph_type = 'digraph'
    else:
        graph_type = 'graph'
    strict = nx.number_of_selfloops(N) == 0 and not N.is_multigraph()

    name = N.name
    graph_defaults = N.graph.get('graph', {})
    if name == '':
        P = pydot.Dot('', graph_type=graph_type, strict=strict,
                      **graph_defaults)
    else:
        P = pydot.Dot('"%s"' % name, graph_type=graph_type, strict=strict,
                      **graph_defaults)
    try:
        P.set_node_defaults(**N.graph['node'])
    except KeyError:
        pass
    try:
        P.set_edge_defaults(**N.graph['edge'])
    except KeyError:
        pass


    P.set('rankdir', 'TB')
    P.set('concentrate', True)
    P.set_node_defaults(shape='record')

    for n, nodedata in N.nodes(data=True):
        str_nodedata = dict((k, str(v)) for k, v in nodedata.items())
        p = pydot.Node(str(n), **str_nodedata)
        P.add_node(p)

    if N.is_multigraph():
        for u, v, key, edgedata in N.edges(data=True, keys=True):
            str_edgedata = dict((k, str(v)) for k, v in edgedata.items()
                                if k != 'key')
            edge = pydot.Edge(str(u), str(v),
                              key=str(key), **str_edgedata)
            P.add_edge(edge)

    else:
        for u, v, edgedata in N.edges(data=True):
            str_edgedata = dict((k, str(v)) for k, v in edgedata.items())
            edge = pydot.Edge(str(u), str(v), **str_edgedata)
            P.add_edge(edge)
    return P


def graphviz_layout(G, prog='neato', root=None):
    """Create node positions using Pydot and Graphviz.

    Returns a dictionary of positions keyed by node.

    Parameters
    ----------
    G : NetworkX Graph
        The graph for which the layout is computed.
    prog : string (default: 'neato')
        The name of the GraphViz program to use for layout.
        Options depend on GraphViz version but may include:
        'dot', 'twopi', 'fdp', 'sfdp', 'circo'
    root : Node from G or None (default: None)
        The node of G from which to start some layout algorithms.

    Returns
    -------
      Dictionary of (x, y) positions keyed by node.

    Examples
    --------
    >>> G = nx.complete_graph(4)
    >>> pos = nx.nx_pydot.graphviz_layout(G)
    >>> pos = nx.nx_pydot.graphviz_layout(G, prog='dot')

    Notes
    -----
    This is a wrapper for pydot_layout.
    """
    return pydot_layout(G=G, prog=prog, root=root)


def pydot_layout(G, prog='neato', root=None):
    """Create node positions using :mod:`pydot` and Graphviz.

    Parameters
    --------
    G : Graph
        NetworkX graph to be laid out.
    prog : string  (default: 'neato')
        Name of the GraphViz command to use for layout.
        Options depend on GraphViz version but may include:
        'dot', 'twopi', 'fdp', 'sfdp', 'circo'
    root : Node from G or None (default: None)
        The node of G from which to start some layout algorithms.

    Returns
    --------
    dict
        Dictionary of positions keyed by node.

    Examples
    --------
    >>> G = nx.complete_graph(4)
    >>> pos = nx.nx_pydot.pydot_layout(G)
    >>> pos = nx.nx_pydot.pydot_layout(G, prog='dot')

    Notes
    -----
    If you use complex node objects, they may have the same string
    representation and GraphViz could treat them as the same node.
    The layout may assign both nodes a single location. See Issue #1568
    If this occurs in your case, consider relabeling the nodes just
    for the layout computation using something similar to:

        H = nx.convert_node_labels_to_integers(G, label_attribute='node_label')
        H_layout = nx.nx_pydot.pydot_layout(G, prog='dot')
        G_layout = {H.nodes[n]['node_label']: p for n, p in H_layout.items()}

    """
    pydot = _import_pydot()
    P = to_pydot(G)
    if root is not None:
        P.set("root", str(root))

    # List of low-level bytes comprising a string in the dot language converted
    # from the passed graph with the passed external GraphViz command.
    D_bytes = P.create_dot(prog=prog)

    # Unique string decoded from these bytes with the preferred locale encoding
    D = unicode(D_bytes, encoding=getpreferredencoding())

    if D == "":  # no data returned
        print("Graphviz layout with %s failed" % (prog))
        print()
        print("To debug what happened try:")
        print("P = nx.nx_pydot.to_pydot(G)")
        print("P.write_dot(\"file.dot\")")
        print("And then run %s on file.dot" % (prog))
        return None

    # List of one or more "pydot.Dot" instances deserialized from this string.
    Q_list = pydot.graph_from_dot_data(D)
    assert len(Q_list) == 1

    # The first and only such instance, as guaranteed by the above assertion.
    Q = Q_list[0]

    node_pos = {}
    for n in G.nodes():
        pydot_node = pydot.Node(str(n)).get_name()
        node = Q.get_node(pydot_node)

        if isinstance(node, list):
            node = node[0]
        pos = node.get_pos()[1:-1]  # strip leading and trailing double quotes
        if pos is not None:
            _x, _y = pos.split(",")
            node_pos[n] = (float(_x), float(_y))

    edge_pos = {}
    for e in list(G.edges):
        src = e[0]
        dst = e[1]
        edge = Q.get_edge(str(src), str(dst))
        if isinstance(edge, list):
            edge = edge[0]
        pos = edge.get_pos()[1:-1]  # strip leading and trailing double quotes
        # Use regex to clean the position string
        pos = re.sub(r'[^\d,.-]+', '', pos)  # Remove unwanted characters
        if pos is not None:
            posxy = pos.split(" ")
            pos_xy = []
            for i in posxy:
                coords = i.split(',')
                if len(coords) == 2:
                    try:
                        pos_xy.append(
                            (float(coords[0].strip()),
                             float(coords[1].strip()))
                        )
                    except ValueError:
                        print(f"Skipping invalid coordinates: {coords}")
            edge_pos[e] = pos_xy
    return node_pos, edge_pos


def _import_pydot():
    '''
    Import and return the `pydot` module if the currently installed version of
    this module satisfies NetworkX requirements _or_ raise an exception.

    Returns
    --------
    :mod:`pydot`
        Imported `pydot` module object.

    Raises
    --------
    ImportError
        If the `pydot` module is unimportable.
    '''

    import pydot
    return pydot

# fixture for nose tests
