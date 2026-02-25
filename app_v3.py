import streamlit as st
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import time
from sklearn.cluster import KMeans

# --- PAGE SETUP ---
st.set_page_config(page_title="Supply Chain Analytics Dashboard", layout="wide")

if "app_mode" not in st.session_state:
    st.session_state.app_mode = "Home"

def go_home():
    st.session_state.app_mode = "Home"

# --- HELPER FUNCTION 1: NETWORK DATA LOADER (Routing, MST, Max Flow) ---
def render_data_loader(key_suffix, weight_col_name="Distance/Cost"):
    state_key = f"network_data_{key_suffix}"
    if state_key not in st.session_state:
        st.session_state[state_key] = pd.DataFrame({
            "Origin": ["Factory", "Factory", "Hub A", "Hub A", "Hub B", "Hub B"],
            "Destination": ["Hub A", "Hub B", "Store 1", "Store 2", "Store 1", "Store 2"],
            weight_col_name: [100.0, 50.0, 40.0, 60.0, 30.0, 20.0]
        })

    col_data1, col_data2 = st.columns([1, 2])
    
    with col_data1:
        st.subheader("1. Upload Network Data")
        uploaded_file = st.file_uploader(f"Upload Excel/CSV", type=["xlsx", "xls", "csv"], key=f"upload_{key_suffix}")
        if uploaded_file is not None:
            file_id_key = f"loaded_{uploaded_file.file_id}_{key_suffix}"
            if file_id_key not in st.session_state:
                try:
                    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                    st.session_state[state_key] = df
                    st.session_state[file_id_key] = True
                    st.success("File loaded successfully!")
                except Exception as e:
                    st.error(f"Error loading file: {e}")

        st.divider()
        st.subheader("2. Modify Network Nodes")
        tab_add, tab_del = st.tabs(["➕ Add Connection", "🗑️ Delete Node"])
        with tab_add:
            with st.form(key=f"add_form_{key_suffix}", clear_on_submit=True):
                new_origin = st.text_input("Starting Node")
                new_dest = st.text_input("Ending Node")
                new_weight = st.number_input(f"Value", min_value=0.0, value=10.0)
                if st.form_submit_button("Add to Network"):
                    if new_origin and new_dest:
                        new_row = pd.DataFrame([{"Origin": new_origin, "Destination": new_dest, weight_col_name: new_weight}])
                        st.session_state[state_key] = pd.concat([st.session_state[state_key], new_row], ignore_index=True)
                        st.rerun()
                        
        with tab_del:
            with st.form(key=f"del_form_{key_suffix}"):
                current_df = st.session_state[state_key]
                node_list = []
                if not current_df.empty and len(current_df.columns) >= 2:
                    node_list = sorted(list(set(current_df.iloc[:,0].dropna()).union(set(current_df.iloc[:,1].dropna()))))
                node_to_delete = st.selectbox("Select Node", node_list)
                if st.form_submit_button("Delete Node"):
                    if node_to_delete:
                        updated_df = current_df[(current_df.iloc[:,0] != node_to_delete) & (current_df.iloc[:,1] != node_to_delete)]
                        st.session_state[state_key] = updated_df
                        st.rerun()

    with col_data2:
        st.subheader("3. Live Network Table")
        edited_df = st.data_editor(st.session_state[state_key], num_rows="dynamic", use_container_width=True, key=f"editor_{key_suffix}") if not st.session_state[state_key].empty else pd.DataFrame()
        st.session_state[state_key] = edited_df
            
    return edited_df

# --- HELPER FUNCTION 2: FACILITY DATA LOADER (Center of Gravity) ---
def render_facility_data_loader(key_suffix):
    state_key = f"facility_data_{key_suffix}"
    if state_key not in st.session_state:
        st.session_state[state_key] = pd.DataFrame({
            "Node_Name": ["Customer A", "Customer B", "Customer C", "Market D", "Market E"],
            "X": [10.0, 20.0, 45.0, 70.0, 80.0],
            "Y": [20.0, 50.0, 15.0, 60.0, 75.0],
            "Weight": [100.0, 150.0, 200.0, 80.0, 120.0]
        })

    col_data1, col_data2 = st.columns([1, 2])
    with col_data1:
        st.subheader("1. Upload Demand Data")
        uploaded_file = st.file_uploader(f"Upload Excel/CSV", type=["xlsx", "xls", "csv"], key=f"fac_up_{key_suffix}")
        if uploaded_file is not None:
            file_id_key = f"fac_load_{uploaded_file.file_id}_{key_suffix}"
            if file_id_key not in st.session_state:
                try:
                    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                    st.session_state[state_key] = df
                    st.session_state[file_id_key] = True
                    st.success("File loaded!")
                except Exception as e: st.error(f"Error: {e}")

        st.divider()
        st.subheader("2. Modify Demand Nodes")
        tab_add, tab_del = st.tabs(["➕ Add Node", "🗑️ Delete Node"])
        with tab_add:
            with st.form(key=f"fac_add_{key_suffix}", clear_on_submit=True):
                new_node = st.text_input("Demand Node Name")
                new_x = st.number_input("X Coordinate", value=0.0)
                new_y = st.number_input("Y Coordinate", value=0.0)
                new_w = st.number_input("Transportation Rate / Vol", min_value=0.0, value=10.0)
                if st.form_submit_button("Add Node"):
                    if new_node:
                        new_row = pd.DataFrame([{"Node_Name": new_node, "X": new_x, "Y": new_y, "Weight": new_w}])
                        st.session_state[state_key] = pd.concat([st.session_state[state_key], new_row], ignore_index=True)
                        st.rerun()
        with tab_del:
            with st.form(key=f"fac_del_{key_suffix}"):
                current_df = st.session_state[state_key]
                node_list = sorted(current_df["Node_Name"].dropna().astype(str).tolist()) if not current_df.empty and "Node_Name" in current_df.columns else []
                node_to_delete = st.selectbox("Select Node", node_list)
                if st.form_submit_button("Delete Node"):
                    if node_to_delete:
                        st.session_state[state_key] = current_df[current_df["Node_Name"].astype(str) != node_to_delete]
                        st.rerun()

    with col_data2:
        st.subheader("3. Live Coordinates Table")
        edited_df = st.data_editor(st.session_state[state_key], num_rows="dynamic", use_container_width=True, key=f"fac_ed_{key_suffix}") if not st.session_state[state_key].empty else pd.DataFrame()
        st.session_state[state_key] = edited_df
    return edited_df

# ==========================================
# SCREEN 1: HOME PAGE
# ==========================================
if st.session_state.app_mode == "Home":
    st.title("📦 Supply Chain Analytics Dashboard")
    st.write("Select an analysis module below to dynamically solve and optimize your supply chain.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("### 🚚 Routing")
        if st.button("Shortest Path", type="primary", use_container_width=True):
            st.session_state.app_mode = "Shortest Path"
            st.rerun()
    with col2:
        st.markdown("### 🌐 Network Design")
        if st.button("Minimal Spanning Tree", type="primary", use_container_width=True):
            st.session_state.app_mode = "MST"
            st.rerun()
    with col3:
        st.markdown("### 🌊 Throughput")
        if st.button("Maximal Flow", type="primary", use_container_width=True):
            st.session_state.app_mode = "Max Flow"
            st.rerun()
    with col4:
        st.markdown("### 📍 Placement")
        if st.button("Facility Location", type="primary", use_container_width=True):
            st.session_state.app_mode = "Facility Location"
            st.rerun()

# ==========================================
# SCREEN 2: SHORTEST PATH TOOL
# ==========================================
elif st.session_state.app_mode == "Shortest Path":
    st.button("⬅️ Back to Home", on_click=go_home)
    st.title("🚚 Shortest Route Optimizer")
    network_df = render_data_loader("sp", "Distance/Cost")
    st.divider()
    
    st.subheader("4. Analysis & Step-by-Step Animation")
    if not network_df.empty and len(network_df.columns) >= 3:
        origin_col, dest_col, cost_col = network_df.columns[0], network_df.columns[1], network_df.columns[2]
        all_nodes = set(network_df[origin_col].dropna()).union(set(network_df[dest_col].dropna()))
        node_list = sorted(list(all_nodes))

        col_sel1, col_sel2, col_sel3 = st.columns(3)
        start_node = col_sel1.selectbox("Starting Location:", node_list, index=0)
        end_node = col_sel2.selectbox("Destination:", node_list, index=max(0, len(node_list)-1))
        algorithm = col_sel3.selectbox("Algorithm:", ["Dijkstra's Algorithm", "Bellman-Ford Algorithm", "Floyd-Warshall Algorithm"])

        if st.button("Calculate & Animate Optimal Route", type="primary"):
            G = nx.Graph() 
            for _, row in network_df.iterrows():
                if not pd.isna(row[origin_col]): G.add_edge(row[origin_col], row[dest_col], weight=float(row[cost_col]))
            
            try:
                if algorithm == "Dijkstra's Algorithm": path = nx.dijkstra_path(G, start_node, end_node, weight="weight")
                elif algorithm == "Bellman-Ford Algorithm": path = nx.bellman_ford_path(G, start_node, end_node, weight="weight")
                else:
                    pred, dist = nx.floyd_warshall_predecessor_and_distance(G, weight='weight')
                    path, curr = [end_node], end_node
                    while curr != start_node:
                        curr = pred[start_node][curr]
                        path.insert(0, curr)
                
                st.success(f"✅ Route Found! Animating path from {start_node} to {end_node}...")
                
                plot_spot = st.empty()
                pos = nx.spring_layout(G, seed=42)
                
                current_path_edges = []
                for i in range(len(path) - 1):
                    current_path_edges.append((path[i], path[i+1]))
                    fig, ax = plt.subplots(figsize=(8, 5))
                    nx.draw(G, pos, with_labels=True, node_color='#E0E0E0', edge_color='#999999', node_size=2000, ax=ax)
                    nx.draw_networkx_edge_labels(G, pos, edge_labels=nx.get_edge_attributes(G, 'weight'), ax=ax)
                    current_nodes = path[:i+2]
                    nx.draw_networkx_nodes(G, pos, nodelist=current_nodes, node_color='#4CAF50', node_size=2000, ax=ax)
                    nx.draw_networkx_edges(G, pos, edgelist=current_path_edges, edge_color='green', width=4, ax=ax)
                    plot_spot.pyplot(fig)
                    time.sleep(0.8) 
            except Exception as e:
                st.error(f"Error: {e}")

# ==========================================
# SCREEN 3: MINIMAL SPANNING TREE TOOL
# ==========================================
elif st.session_state.app_mode == "MST":
    st.button("⬅️ Back to Home", on_click=go_home)
    st.title("🌐 Minimal Spanning Tree (MST) Designer")
    network_df = render_data_loader("mst", "Distance/Cost")
    st.divider()
    
    st.subheader("4. Analysis & Step-by-Step Animation")
    if not network_df.empty and len(network_df.columns) >= 3:
        mst_algorithm = st.selectbox("Select Algorithm:", ["Kruskal's Algorithm", "Prim's Algorithm"])
        
        if st.button("Calculate & Animate Network Design", type="primary"):
            origin_col, dest_col, cost_col = network_df.columns[0], network_df.columns[1], network_df.columns[2]
            G = nx.Graph() 
            for _, row in network_df.iterrows():
                if not pd.isna(row[origin_col]): G.add_edge(row[origin_col], row[dest_col], weight=float(row[cost_col]))
            
            try:
                selected_algo = "kruskal" if mst_algorithm == "Kruskal's Algorithm" else "prim"
                MST = nx.minimum_spanning_tree(G, weight='weight', algorithm=selected_algo)
                
                st.success(f"✅ MST Calculated! Animating tree construction...")
                
                plot_spot = st.empty()
                pos = nx.spring_layout(G, seed=42)
                
                sorted_mst_edges = sorted(MST.edges(data=True), key=lambda x: x[2]['weight'])
                current_mst_edges = []
                
                for u, v, d in sorted_mst_edges:
                    current_mst_edges.append((u, v))
                    fig, ax = plt.subplots(figsize=(8, 5))
                    nx.draw(G, pos, with_labels=True, node_color='#E0E0E0', edge_color='#D3D3D3', style='dashed', node_size=2000, ax=ax)
                    nx.draw_networkx_edges(G, pos, edgelist=current_mst_edges, edge_color='#2196F3', width=4, ax=ax)
                    current_labels = {(n1, n2): G[n1][n2]['weight'] for n1, n2 in current_mst_edges}
                    nx.draw_networkx_edge_labels(G, pos, edge_labels=current_labels, font_color='blue', ax=ax)
                    plot_spot.pyplot(fig)
                    time.sleep(0.7) 
            except Exception as e:
                st.error(f"Error: {e}")

# ==========================================
# SCREEN 4: MAXIMAL FLOW MODEL
# ==========================================
elif st.session_state.app_mode == "Max Flow":
    st.button("⬅️ Back to Home", on_click=go_home)
    st.title("🌊 Maximal Flow Network Optimizer")
    network_df = render_data_loader("mf", "Capacity")
    st.divider()
    
    st.subheader("4. Analysis & Step-by-Step Animation")
    if not network_df.empty and len(network_df.columns) >= 3:
        origin_col, dest_col, cap_col = network_df.columns[0], network_df.columns[1], network_df.columns[2]
        all_nodes = set(network_df[origin_col].dropna()).union(set(network_df[dest_col].dropna()))
        node_list = sorted(list(all_nodes))

        col_sel1, col_sel2, col_sel3 = st.columns(3)
        start_node = col_sel1.selectbox("Source Node:", node_list, index=0)
        end_node = col_sel2.selectbox("Sink Node:", node_list, index=max(0, len(node_list)-1))
        algorithm = col_sel3.selectbox("Algorithm:", ["Preflow-Push", "Edmonds-Karp", "Shortest Augmenting Path"])

        if st.button("Calculate & Animate Maximum Flow", type="primary"):
            G = nx.DiGraph() 
            for _, row in network_df.iterrows():
                if not pd.isna(row[origin_col]): G.add_edge(row[origin_col], row[dest_col], capacity=max(0.0, float(row[cap_col])))
            
            try:
                flow_func_map = {"Preflow-Push": nx.algorithms.flow.preflow_push, "Edmonds-Karp": nx.algorithms.flow.edmonds_karp, "Shortest Augmenting Path": nx.algorithms.flow.shortest_augmenting_path}
                flow_value, flow_dict = nx.maximum_flow(G, start_node, end_node, capacity='capacity', flow_func=flow_func_map[algorithm])
                
                st.success(f"✅ Max Flow Calculated: {flow_value}. Identifying bottlenecks...")
                
                edge_labels, bottleneck_edges, normal_edges = {}, [], []
                for u, v, d in G.edges(data=True):
                    cap, actual_flow = d['capacity'], flow_dict[u][v]
                    edge_labels[(u, v)] = f"{actual_flow}/{cap}"
                    if actual_flow == cap and cap > 0: bottleneck_edges.append((u, v))
                    else: normal_edges.append((u, v))

                plot_spot = st.empty()
                pos = nx.spring_layout(G, seed=42)
                
                fig, ax = plt.subplots(figsize=(8, 6))
                nx.draw_networkx_nodes(G, pos, node_color='#FFB74D', node_size=2000, ax=ax)
                nx.draw_networkx_labels(G, pos, ax=ax)
                nx.draw_networkx_edges(G, pos, edgelist=G.edges(), edge_color='#B0BEC5', arrows=True, width=2, ax=ax)
                nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9, ax=ax)
                plot_spot.pyplot(fig)
                time.sleep(1.0)
                
                current_bottlenecks = []
                for edge in bottleneck_edges:
                    current_bottlenecks.append(edge)
                    fig, ax = plt.subplots(figsize=(8, 6))
                    nx.draw_networkx_nodes(G, pos, node_color='#FFB74D', node_size=2000, ax=ax)
                    nx.draw_networkx_labels(G, pos, ax=ax)
                    nx.draw_networkx_edges(G, pos, edgelist=normal_edges, edge_color='#B0BEC5', arrows=True, width=2, ax=ax)
                    nx.draw_networkx_edges(G, pos, edgelist=current_bottlenecks, edge_color='#F44336', arrows=True, width=4, ax=ax)
                    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9, ax=ax)
                    plot_spot.pyplot(fig)
                    time.sleep(0.8)
            except Exception as e:
                st.error(f"Error: {e}")

# ==========================================
# SCREEN 5: FACILITY LOCATION MODEL
# ==========================================
elif st.session_state.app_mode == "Facility Location":
    st.button("⬅️ Back to Home", on_click=go_home)
    st.title("📍 Facility Location Optimizer")
    
    fac_df = render_facility_data_loader("fac")
    st.divider()
    
    if not fac_df.empty and len(fac_df.columns) >= 4:
        name_col, x_col, y_col, w_col = fac_df.columns[0], fac_df.columns[1], fac_df.columns[2], fac_df.columns[3]
        
        # Coerce to numeric
        fac_df[x_col] = pd.to_numeric(fac_df[x_col], errors='coerce')
        fac_df[y_col] = pd.to_numeric(fac_df[y_col], errors='coerce')
        fac_df[w_col] = pd.to_numeric(fac_df[w_col], errors='coerce')
        fac_df = fac_df.dropna()

        tab_cog, tab_mcog = st.tabs(["Single Facility (COG)", "Multi-Facility (Multi-COG)"])
        
        with tab_cog:
            st.subheader("Calculate Optimal Single Hub")
            
            if st.button("Locate Single Facility", type="primary"):
                total_w = fac_df[w_col].sum()
                cx = (fac_df[x_col] * fac_df[w_col]).sum() / total_w
                cy = (fac_df[y_col] * fac_df[w_col]).sum() / total_w
                
                fac_df['Distance'] = np.sqrt((fac_df[x_col] - cx)**2 + (fac_df[y_col] - cy)**2)
                total_cost = (fac_df[w_col] * fac_df['Distance']).sum()
                
                st.success(f"✅ Optimal Location Found at Coordinates: ({cx:.2f}, {cy:.2f})")
                st.markdown(f"**Total Transportation Score:** {total_cost:,.2f}")
                
                fig, ax = plt.subplots(figsize=(8, 6))
                sizes = fac_df[w_col] * 3 
                ax.scatter(fac_df[x_col], fac_df[y_col], s=sizes, c='#2196F3', alpha=0.6, label="Demand Nodes")
                for i, txt in enumerate(fac_df[name_col]):
                    ax.annotate(txt, (fac_df[x_col].iloc[i]+1, fac_df[y_col].iloc[i]+1), fontsize=9)
                
                ax.scatter(cx, cy, s=200, c='red', marker='*', label="Optimal Facility")
                for i in range(len(fac_df)):
                    ax.plot([cx, fac_df[x_col].iloc[i]], [cy, fac_df[y_col].iloc[i]], 'r--', alpha=0.3)
                
                ax.set_xlabel("X Coordinate")
                ax.set_ylabel("Y Coordinate")
                ax.legend()
                ax.grid(True, linestyle=':', alpha=0.6)
                st.pyplot(fig)

        with tab_mcog:
            st.subheader("Calculate Multiple Hubs (K-Means)")
            k_val = st.number_input("Number of Facilities to Locate:", min_value=1, max_value=max(1, len(fac_df)), value=2)
            
            if st.button("Locate Multiple Facilities", type="primary"):
                kmeans = KMeans(n_clusters=int(k_val), random_state=42, n_init=10)
                kmeans.fit(fac_df[[x_col, y_col]], sample_weight=fac_df[w_col])
                
                fac_df['Cluster'] = kmeans.labels_
                centers = kmeans.cluster_centers_
                
                total_mcog_cost = 0
                for i in range(k_val):
                    c_df = fac_df[fac_df['Cluster'] == i]
                    dists = np.sqrt((c_df[x_col] - centers[i][0])**2 + (c_df[y_col] - centers[i][1])**2)
                    total_mcog_cost += (c_df[w_col] * dists).sum()
                
                st.success(f"✅ {k_val} Optimal Locations Found! Total Score: {total_mcog_cost:,.2f}")
                
                fig, ax = plt.subplots(figsize=(8, 6))
                colors = plt.cm.get_cmap('tab10', k_val)
                
                for i in range(k_val):
                    cluster_points = fac_df[fac_df['Cluster'] == i]
                    ax.scatter(cluster_points[x_col], cluster_points[y_col], 
                               s=cluster_points[w_col]*3, color=colors(i), alpha=0.6, label=f"Cluster {i+1}")
                    
                    ax.scatter(centers[i][0], centers[i][1], s=250, color=colors(i), marker='*', edgecolor='black', zorder=5)
                    ax.annotate(f"Hub {i+1}", (centers[i][0]+1, centers[i][1]+1), fontweight='bold')
                    
                    for _, row in cluster_points.iterrows():
                        ax.plot([centers[i][0], row[x_col]], [centers[i][1], row[y_col]], color=colors(i), linestyle='--', alpha=0.4)
                        ax.annotate(row[name_col], (row[x_col]+1, row[y_col]+1), fontsize=8)

                ax.set_xlabel("X Coordinate")
                ax.set_ylabel("Y Coordinate")
                ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                ax.grid(True, linestyle=':', alpha=0.6)
                plt.tight_layout()
                st.pyplot(fig)
    else:
        st.warning("Please ensure your data has 4 columns: Name, X, Y, and Weight/Volume.")