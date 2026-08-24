"""
Step 3: Knowledge Graph Construction
----------------------------------
Goal: Turn the resolved entities (from Step 2) into an actual graph structure,
so relationships between a person and their assets/filings are explicit and
queryable — this is the "Knowledge Graph" part of the problem statement.

Graph design:
    Nodes:
        - Person nodes   (from resolved_entities.csv)
        - Vehicle nodes  (engine_cc as an attribute)
        - Bill nodes     (monthly_bill_pkr as an attribute)
        - Filing nodes   (declared_income as an attribute)

    Edges:
        - Person -> OWNS -> Vehicle
        - Person -> PAYS -> Bill
        - Person -> FILED -> Filing

We use networkx (pure Python, no extra install needed) to build and later
visualize/query this graph. This sets up Step 4 (Anomaly Scoring), where
we'll walk the graph for each person and check: does their vehicle/bill
"lifestyle" match their declared tax filing?
"""

import csv
import os
import networkx as nx

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_graph(resolved_entities):
    G = nx.DiGraph()  

    for row in resolved_entities:
        person_node = f"Person:{row['resolved_id']}"
        G.add_node(
            person_node,
            type="Person",
            name=row["filer_name"],
            cnic=row["cnic"],
        )

       
        filing_node = f"Filing:{row['resolved_id']}"
        G.add_node(
            filing_node,
            type="Filing",
            declared_income=row["declared_income"],
            filed_return=row["filed_return"],
        )
        G.add_edge(person_node, filing_node, relation="FILED")

      
        if row["vehicle_owner_name"]:
            vehicle_node = f"Vehicle:{row['resolved_id']}"
            G.add_node(
                vehicle_node,
                type="Vehicle",
                engine_cc=row["engine_cc"],
            )
            G.add_edge(person_node, vehicle_node, relation="OWNS")

       
        if row["bill_consumer_name"]:
            bill_node = f"Bill:{row['resolved_id']}"
            G.add_node(
                bill_node,
                type="Bill",
                monthly_bill_pkr=row["monthly_bill_pkr"],
            )
            G.add_edge(person_node, bill_node, relation="PAYS")

    return G


def print_graph_summary(G):
    node_types = {}
    for _, data in G.nodes(data=True):
        t = data.get("type", "unknown")
        node_types[t] = node_types.get(t, 0) + 1

    print("\n--- Knowledge Graph Summary ---")
    print(f"Total nodes: {G.number_of_nodes()}")
    print(f"Total edges: {G.number_of_edges()}")
    for t, count in node_types.items():
        print(f"  {t} nodes: {count}")


def print_sample_person(G, resolved_id="E0003"):
    """Show one person's full connected subgraph as a sanity check."""
    person_node = f"Person:{resolved_id}"
    if person_node not in G:
        print(f"\n(no node found for {resolved_id})")
        return

    print(f"\n--- Sample: {person_node} ---")
    print(f"Attributes: {G.nodes[person_node]}")
    for neighbor in G.successors(person_node):
        edge_data = G.edges[person_node, neighbor]
        print(f"  -> [{edge_data['relation']}] {neighbor} | {G.nodes[neighbor]}")


def save_graph(G, filename="knowledge_graph.graphml"):
    """
    Save in GraphML format -> can be opened in Gephi or other graph
    visualization tools if you want a polished visual for your CV/report.
    """
    path = os.path.join(DATA_DIR, filename)
    nx.write_graphml(G, path)
    print(f"\nSaved graph -> {path}")
    print("(You can open this .graphml file in Gephi for a visual graph image)")


if __name__ == "__main__":
    resolved_entities = load_csv("resolved_entities.csv")
    print(f"Loaded {len(resolved_entities)} resolved entities")

    G = build_graph(resolved_entities)
    print_graph_summary(G)
    print_sample_person(G, "E0003")  
    save_graph(G)
