import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# Create output directories
os.makedirs('csv_output', exist_ok=True)
os.makedirs('charts', exist_ok=True)

# Load the JSON data
with open('RINA/rina_metrics.json', 'r') as f:
    rina_data = json.load(f)

with open('RINA/tcp_metrics.json', 'r') as f:
    tcp_data = json.load(f)

with open('RINA/hybrid_metrics.json', 'r') as f:
    hybrid_data = json.load(f)

# 1. THROUGHPUT COMPARISON
def extract_throughput_data():
    # Initialize dataframes for each network type
    networks = ['perfect', 'lan', 'wifi', 'congested']
    packet_sizes = [64, 512, 1024, 4096, 8192]
    
    all_data = []
    
    # Extract TCP data
    for network in networks:
        for size in packet_sizes:
            if str(size) in tcp_data['throughput_tcp_network'][network]:
                row = {
                    'Protocol': 'TCP',
                    'Network': network,
                    'Packet_Size': size,
                    'Throughput_Mbps': tcp_data['throughput_tcp_network'][network][str(size)]['throughput_mbps'],
                    'Delivery_Ratio': tcp_data['throughput_tcp_network'][network][str(size)]['delivery_ratio']
                }
                all_data.append(row)
    
    # Extract RINA data
    for network in networks:
        for size in packet_sizes:
            if str(size) in rina_data['throughput_realistic_networks'][network]:
                row = {
                    'Protocol': 'RINA',
                    'Network': network,
                    'Packet_Size': size,
                    'Throughput_Mbps': rina_data['throughput_realistic_networks'][network][str(size)]['throughput_mbps'],
                    'Delivery_Ratio': 100.0  # Not directly available in the same way, using placeholder
                }
                all_data.append(row)
    
    # Extract Hybrid data
    for network in networks:
        for size in packet_sizes:
            if str(size) in hybrid_data['throughput_hybrid_network'][network]:
                row = {
                    'Protocol': 'Hybrid',
                    'Network': network,
                    'Packet_Size': size,
                    'Throughput_Mbps': hybrid_data['throughput_hybrid_network'][network][str(size)]['throughput_mbps'],
                    'Delivery_Ratio': hybrid_data['throughput_hybrid_network'][network][str(size)]['delivery_ratio']
                }
                all_data.append(row)
    
    # Create dataframe
    df = pd.DataFrame(all_data)
    
    # Save to CSV
    df.to_csv('csv_output/throughput_comparison.csv', index=False)
    
    return df

# 2. LATENCY COMPARISON
def extract_latency_data():
    networks = ['perfect', 'lan', 'wifi', 'congested']
    packet_sizes = [64, 512, 1024, 4096]
    
    all_data = []
    
    # Extract TCP latency data
    for network in networks:
        for size in packet_sizes:
            if str(size) in tcp_data['latency_jitter_tcp'][network]:
                row = {
                    'Protocol': 'TCP',
                    'Network': network,
                    'Packet_Size': size,
                    'Avg_Latency_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['avg_latency_ms'],
                    'Min_Latency_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['min_latency_ms'],
                    'Max_Latency_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['max_latency_ms'],
                    'Avg_Jitter_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['avg_jitter_ms'],
                    'Avg_RTT_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['avg_rtt_ms']
                }
                all_data.append(row)
    
    # Extract RINA latency data
    for network in networks:
        for size in packet_sizes:
            if str(size) in rina_data['latency_jitter_realistic'][network]:
                row = {
                    'Protocol': 'RINA',
                    'Network': network,
                    'Packet_Size': size,
                    'Avg_Latency_ms': rina_data['latency_jitter_realistic'][network][str(size)]['avg_latency_ms'],
                    'Min_Latency_ms': rina_data['latency_jitter_realistic'][network][str(size)]['min_latency_ms'],
                    'Max_Latency_ms': rina_data['latency_jitter_realistic'][network][str(size)]['max_latency_ms'],
                    'Avg_Jitter_ms': rina_data['latency_jitter_realistic'][network][str(size)]['avg_jitter_ms'],
                    'Avg_RTT_ms': rina_data['latency_jitter_realistic'][network][str(size)]['avg_rtt_ms']
                }
                all_data.append(row)
    
    # Extract Hybrid latency data
    for network in networks:
        for size in packet_sizes:
            if str(size) in hybrid_data['latency_jitter_hybrid'][network]:
                row = {
                    'Protocol': 'Hybrid',
                    'Network': network,
                    'Packet_Size': size,
                    'Avg_Latency_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['avg_latency_ms'],
                    'Min_Latency_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['min_latency_ms'],
                    'Max_Latency_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['max_latency_ms'],
                    'Avg_Jitter_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['avg_jitter_ms'],
                    'Avg_RTT_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['avg_rtt_ms']
                }
                all_data.append(row)
    
    # Create dataframe
    df = pd.DataFrame(all_data)
    
    # Save to CSV
    df.to_csv('csv_output/latency_comparison.csv', index=False)
    
    return df

# 3. PACKET DELIVERY RATIO COMPARISON
def extract_pdr_data():
    networks = ['perfect', 'lan', 'wifi', 'congested']
    packet_sizes = [64, 1024, 4096]  # Some datasets don't have all sizes
    
    all_data = []
    
    # Extract TCP data
    for network in networks:
        for size in [64, 1024, 4096]:  # TCP only has 64 and 1024
            if str(size) in tcp_data['packet_delivery_ratio_tcp'][network]:
                row = {
                    'Protocol': 'TCP',
                    'Network': network,
                    'Packet_Size': size,
                    'Sent': tcp_data['packet_delivery_ratio_tcp'][network][str(size)]['sent'],
                    'Received': tcp_data['packet_delivery_ratio_tcp'][network][str(size)]['received'],
                    'Delivery_Ratio': tcp_data['packet_delivery_ratio_tcp'][network][str(size)]['delivery_ratio']
                }
                all_data.append(row)
    
    # Extract RINA data
    for network in networks:
        for size in packet_sizes:
            if str(size) in rina_data['packet_delivery_ratio_realistic'][network]:
                row = {
                    'Protocol': 'RINA',
                    'Network': network,
                    'Packet_Size': size,
                    'Sent': rina_data['packet_delivery_ratio_realistic'][network][str(size)]['sent'],
                    'Received': rina_data['packet_delivery_ratio_realistic'][network][str(size)]['received'],
                    'Delivery_Ratio': rina_data['packet_delivery_ratio_realistic'][network][str(size)]['delivery_ratio']
                }
                all_data.append(row)
    
    # Extract Hybrid data
    for network in networks:
        for size in [64, 1024, 4096]:  # Hybrid only has 64 and 1024
            if str(size) in hybrid_data['packet_delivery_ratio_hybrid'][network]:
                row = {
                    'Protocol': 'Hybrid',
                    'Network': network,
                    'Packet_Size': size,
                    'Sent': hybrid_data['packet_delivery_ratio_hybrid'][network][str(size)]['sent'],
                    'Received': hybrid_data['packet_delivery_ratio_hybrid'][network][str(size)]['received'],
                    'Delivery_Ratio': hybrid_data['packet_delivery_ratio_hybrid'][network][str(size)]['delivery_ratio']
                }
                all_data.append(row)
    
    # Create dataframe
    df = pd.DataFrame(all_data)
    
    # Save to CSV
    df.to_csv('csv_output/packet_delivery_ratio.csv', index=False)
    
    return df

# 4. CONCURRENT CONNECTIONS/FLOWS
def extract_concurrent_data():
    connection_counts = [1, 5, 10, 25]  # 50 only in RINA
    
    all_data = []
    
    # Extract TCP data
    for count in [1, 5, 10, 25]:  # TCP doesn't have 50
        row = {
            'Protocol': 'TCP',
            'Target_Count': count,
            'Successful_Count': tcp_data['concurrent_tcp_connections'][str(count)]['successful_connections'],
            'Establishment_Time_ms': tcp_data['concurrent_tcp_connections'][str(count)]['establishment_time_per_conn_ms'],
            'Success_Rate': tcp_data['concurrent_tcp_connections'][str(count)]['data_exchange_success_rate']
        }
        all_data.append(row)
    
    # Extract RINA data for perfect network
    for count in connection_counts:
        if str(count) in rina_data['scalability_concurrent_flows']['perfect']:
            row = {
                'Protocol': 'RINA',
                'Target_Count': count,
                'Successful_Count': rina_data['scalability_concurrent_flows']['perfect'][str(count)]['successful_flows'],
                'Establishment_Time_ms': rina_data['scalability_concurrent_flows']['perfect'][str(count)]['allocation_time_per_flow_ms'],
                'Success_Rate': rina_data['scalability_concurrent_flows']['perfect'][str(count)]['data_send_success_rate'],
                'Bandwidth_Per_Flow_Mbps': rina_data['scalability_concurrent_flows']['perfect'][str(count)]['bandwidth_per_flow_mbps']
            }
            all_data.append(row)
    
    # Extract Hybrid data
    for count in [1, 5, 10, 25]:  # Hybrid doesn't have 50
        row = {
            'Protocol': 'Hybrid',
            'Target_Count': count,
            'Successful_Count': hybrid_data['concurrent_tcp_connections'][str(count)]['successful_connections'],
            'Establishment_Time_ms': hybrid_data['concurrent_tcp_connections'][str(count)]['establishment_time_per_conn_ms'],
            'Success_Rate': hybrid_data['concurrent_tcp_connections'][str(count)]['data_exchange_success_rate']
        }
        all_data.append(row)
    
    # Create dataframe
    df = pd.DataFrame(all_data)
    
    # Save to CSV
    df.to_csv('csv_output/concurrent_connections.csv', index=False)
    
    return df

# VISUALIZATIONS

# 1. Throughput comparison across protocols and networks
def plot_throughput_comparison(df):
    # Get unique network profiles
    networks = df['Network'].unique()
    
    # Create a separate chart for each network profile
    for network in networks:
        # Filter data for this network
        network_df = df[df['Network'] == network]
        
        # Create figure
        plt.figure(figsize=(10, 6))
        
        # Create bar chart
        sns.barplot(x='Packet_Size', y='Throughput_Mbps', hue='Protocol', 
                   data=network_df, errorbar=None, palette='viridis')
        
        # Add titles and labels
        plt.title(f'Throughput Comparison - {network.capitalize()} Network')
        plt.xlabel('Packet Size (bytes)')
        plt.ylabel('Throughput (Mbps)')
        plt.legend(title='Protocol')
        
        # Save the figure
        plt.tight_layout()
        plt.savefig(f'charts/throughput_{network}_network.png', dpi=300)
        plt.close()
        
        # Create log scale version for better visibility of small values
        plt.figure(figsize=(10, 6))
        
        # Create bar chart
        ax = sns.barplot(x='Packet_Size', y='Throughput_Mbps', hue='Protocol', 
                       data=network_df, errorbar=None, palette='viridis')
        
        # Set y-axis to log scale
        ax.set_yscale('log')
        
        # Add titles and labels
        plt.title(f'Throughput Comparison - {network.capitalize()} Network (Log Scale)')
        plt.xlabel('Packet Size (bytes)')
        plt.ylabel('Throughput (Mbps) - Log Scale')
        plt.legend(title='Protocol')
        
        # Save the figure
        plt.tight_layout()
        plt.savefig(f'charts/throughput_{network}_network_log.png', dpi=300)
        plt.close()
    
    # Also create a consolidated view with all networks in one figure
    plt.figure(figsize=(16, 10))
    
    # Create facet grid with one chart per network
    g = sns.FacetGrid(df, col='Network', height=5, aspect=1.2)
    g.map_dataframe(sns.barplot, x='Packet_Size', y='Throughput_Mbps', 
                   hue='Protocol', errorbar=None, palette='viridis')
    
    # Add titles and labels
    g.set_axis_labels('Packet Size (bytes)', 'Throughput (Mbps)')
    g.set_titles(col_template='{col_name} Network')
    g.add_legend(title='Protocol')
    
    # Save the figure
    plt.tight_layout()
    plt.savefig('charts/throughput_all_networks.png', dpi=300)
    plt.close()

# 2. Latency comparison
def plot_latency_comparison(df):
    # Filter out congested network for better scale in first plot
    df_no_congested = df[df['Network'] != 'congested']
    
    plt.figure(figsize=(14, 8))
    
    # Create facet grid by network and packet size
    g = sns.FacetGrid(df_no_congested, col='Network', row='Packet_Size', height=3, aspect=1.5)
    g.map_dataframe(sns.barplot, x='Protocol', y='Avg_Latency_ms', errorbar=None, palette='cool')
    
    g.set_axis_labels('Protocol', 'Average Latency (ms)')
    g.set_titles(col_template='{col_name} Network', row_template='Packet Size: {row_name} bytes')
    
    plt.tight_layout()
    plt.savefig('charts/latency_comparison_no_congested.png', dpi=300)
    
    # Create a separate plot for all networks including congested
    g = sns.FacetGrid(df, col='Network', row='Packet_Size', height=3, aspect=1.5)
    g.map_dataframe(sns.barplot, x='Protocol', y='Avg_Latency_ms', errorbar=None, palette='cool')
    
    g.set_axis_labels('Protocol', 'Average Latency (ms)')
    g.set_titles(col_template='{col_name} Network', row_template='Packet Size: {row_name} bytes')
    
    plt.tight_layout()
    plt.savefig('charts/latency_comparison_all.png', dpi=300)
    
    # Plot jitter comparison
    g = sns.FacetGrid(df, col='Network', height=5, aspect=1.2)
    g.map_dataframe(sns.barplot, x='Protocol', y='Avg_Jitter_ms', hue='Packet_Size', errorbar=None, palette='rocket')
    
    g.set_axis_labels('Protocol', 'Average Jitter (ms)')
    g.set_titles(col_template='{col_name} Network')
    g.add_legend(title='Packet Size (bytes)')
    
    plt.tight_layout()
    plt.savefig('charts/jitter_comparison.png', dpi=300)

def plot_jitter_comparison(df):
    plt.figure(figsize=(16, 8))
    g = sns.FacetGrid(df, col='Network', height=6, aspect=1.2)
    g.map_dataframe(sns.barplot, x='Packet_Size', y='Avg_Jitter_ms', 
                   hue='Protocol', errorbar=None, palette='Set2')
    
    g.set_axis_labels('Packet Size (bytes)', 'Average Jitter (ms)')
    g.set_titles(col_template='{col_name} Network')
    g.add_legend(title='Protocol')
    
    # Improve readability
    for ax in g.axes.flat:
        ax.grid(True, linestyle='--', alpha=0.6)
        for label in ax.get_xticklabels():
            label.set_rotation(45)
    
    plt.tight_layout()
    plt.savefig('charts/jitter_by_network_packetsize.png', dpi=300)
    
    # 2. Protocol-focused jitter comparison
    plt.figure(figsize=(16, 8))
    g = sns.FacetGrid(df, col='Protocol', height=6, aspect=1.2)
    g.map_dataframe(sns.barplot, x='Network', y='Avg_Jitter_ms', 
                   hue='Packet_Size', errorbar=None, palette='viridis')
    
    g.set_axis_labels('Network Type', 'Average Jitter (ms)')
    g.set_titles(col_template='{col_name} Protocol')
    g.add_legend(title='Packet Size (bytes)')
    
    # Improve readability
    for ax in g.axes.flat:
        ax.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig('charts/jitter_by_protocol_network.png', dpi=300)
    
    # 3. Heatmap visualization for jitter comparison
    pivot_df = df.pivot_table(
        index=['Protocol', 'Packet_Size'], 
        columns='Network', 
        values='Avg_Jitter_ms'
    )
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(pivot_df, annot=True, cmap='YlGnBu', fmt='.2f', linewidths=.5)
    plt.title('Average Jitter (ms) Across Networks, Protocols and Packet Sizes')
    plt.tight_layout()
    plt.savefig('charts/jitter_heatmap.png', dpi=300)
    
    # 4. Box plot to show jitter distribution and variability
    plt.figure(figsize=(18, 10))
    g = sns.FacetGrid(df, col='Network', row='Protocol', height=4, aspect=1.3)
    g.map_dataframe(sns.boxplot, x='Packet_Size', y='Avg_Jitter_ms', palette='Set3')
    
    g.set_axis_labels('Packet Size (bytes)', 'Average Jitter (ms)')
    g.set_titles(col_template='{col_name} Network', row_template='{row_name}')
    
    # Improve readability
    for ax in g.axes.flat:
        if ax is not None:
            ax.grid(True, linestyle='--', alpha=0.6)
            for label in ax.get_xticklabels():
                label.set_rotation(45)
    
    plt.tight_layout()
    plt.savefig('charts/jitter_boxplot_by_protocol_network.png', dpi=300)
    
    # 5. Line plot showing jitter trends
    plt.figure(figsize=(14, 8))
    sns.lineplot(data=df, x='Packet_Size', y='Avg_Jitter_ms', 
                 hue='Protocol', style='Network', markers=True, 
                 linewidth=2.5, palette='Dark2')
    
    plt.title('Jitter Trends Across Packet Sizes')
    plt.xlabel('Packet Size (bytes)')
    plt.ylabel('Average Jitter (ms)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(title='', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig('charts/jitter_trends_line.png', dpi=300)

    # 6. Violin plot for jitter distribution
    plt.figure(figsize=(16, 10))
    sns.violinplot(data=df, x='Protocol', y='Avg_Jitter_ms', 
                  hue='Network', split=True, palette='Set1')
    
    plt.title('Jitter Distribution by Protocol and Network')
    plt.xlabel('Protocol')
    plt.ylabel('Average Jitter (ms)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(title='Network Type')
    plt.tight_layout()
    plt.savefig('charts/jitter_violin_plot.png', dpi=300)
    
    # 7. Correlation between jitter and latency
    plt.figure(figsize=(10, 8))
    sns.scatterplot(data=df, x='Avg_Latency_ms', y='Avg_Jitter_ms', 
                   hue='Protocol', style='Network', size='Packet_Size',
                   sizes=(50, 200), alpha=0.7)
    
    plt.title('Correlation Between Latency and Jitter')
    plt.xlabel('Average Latency (ms)')
    plt.ylabel('Average Jitter (ms)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(title='', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig('charts/jitter_latency_correlation.png', dpi=300)

    print("jitter visualization charts created successfully!")

# 3. Packet Delivery Ratio comparison
def plot_pdr_comparison(df):
    plt.figure(figsize=(14, 8))
    
    # Create facet grid by network and packet size
    g = sns.FacetGrid(df, col='Network', row='Packet_Size', height=3, aspect=1.5)
    g.map_dataframe(sns.barplot, x='Protocol', y='Delivery_Ratio', errorbar=None, palette='mako')
    
    g.set_axis_labels('Protocol', 'Packet Delivery Ratio (%)')
    g.set_titles(col_template='{col_name} Network', row_template='Packet Size: {row_name} bytes')
    
    # Set y-axis limits for better comparison
    for ax in g.axes.flat:
        ax.set_ylim(0, 105)  # Slightly above 100% for clear view
    
    plt.tight_layout()
    plt.savefig('charts/packet_delivery_ratio.png', dpi=300)
    
    # Focus on congested network only
    df_congested = df[df['Network'] == 'congested']
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_congested, x='Protocol', y='Delivery_Ratio', hue='Packet_Size', errorbar=None, palette='mako')
    plt.title('Packet Delivery Ratio in Congested Network')
    plt.ylabel('Delivery Ratio (%)')
    plt.ylim(0, 100)
    plt.legend(title='Packet Size (bytes)')
    plt.tight_layout()
    plt.savefig('charts/pdr_congested.png', dpi=300)

# 4. Concurrent Connections/Flows
def plot_concurrent_comparison(df):
    plt.figure(figsize=(12, 7))
    
    # Plot establishment time vs connection count
    sns.lineplot(data=df, x='Target_Count', y='Establishment_Time_ms', hue='Protocol', 
                marker='o', palette='tab10', linewidth=2.5)
    
    plt.title('Connection/Flow Establishment Time per Count')
    plt.xlabel('Number of Concurrent Connections/Flows')
    plt.ylabel('Establishment Time per Connection (ms)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('charts/concurrent_establishment_time.png', dpi=300)
    
    # Log scale version
    plt.figure(figsize=(12, 7))
    sns.lineplot(data=df, x='Target_Count', y='Establishment_Time_ms', hue='Protocol', 
                marker='o', palette='tab10', linewidth=2.5)
    plt.yscale('log')
    plt.title('Connection/Flow Establishment Time (Log Scale)')
    plt.xlabel('Number of Concurrent Connections/Flows')
    plt.ylabel('Establishment Time per Connection (ms) - Log Scale')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('charts/concurrent_establishment_time_log.png', dpi=300)
    
    # RINA-specific plot for bandwidth allocation
    if 'Bandwidth_Per_Flow_Mbps' in df.columns:
        rina_df = df[df['Protocol'] == 'RINA']
        if not rina_df.empty:
            plt.figure(figsize=(10, 6))
            sns.lineplot(data=rina_df, x='Target_Count', y='Bandwidth_Per_Flow_Mbps', 
                        marker='o', color='green', linewidth=2.5)
            plt.title('RINA Bandwidth Allocation per Flow')
            plt.xlabel('Number of Concurrent Flows')
            plt.ylabel('Bandwidth per Flow (Mbps)')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            plt.savefig('charts/rina_bandwidth_allocation.png', dpi=300)

# 5. Summary comparison
def create_summary_comparison():
    # Create a summary table comparing key metrics
    throughput_df = pd.read_csv('csv_output/throughput_comparison.csv')
    latency_df = pd.read_csv('csv_output/latency_comparison.csv')
    pdr_df = pd.read_csv('csv_output/packet_delivery_ratio.csv')
    
    # Average throughput by protocol and network
    throughput_summary = throughput_df.groupby(['Protocol', 'Network'])['Throughput_Mbps'].mean().reset_index()
    throughput_summary = throughput_summary.pivot(index='Protocol', columns='Network', values='Throughput_Mbps')
    throughput_summary.columns = [f'Avg_Throughput_{col}' for col in throughput_summary.columns]
    
    # Average latency by protocol and network
    latency_summary = latency_df.groupby(['Protocol', 'Network'])['Avg_Latency_ms'].mean().reset_index()
    latency_summary = latency_summary.pivot(index='Protocol', columns='Network', values='Avg_Latency_ms')
    latency_summary.columns = [f'Avg_Latency_{col}' for col in latency_summary.columns]
    
    # Average PDR by protocol and network
    pdr_summary = pdr_df.groupby(['Protocol', 'Network'])['Delivery_Ratio'].mean().reset_index()
    pdr_summary = pdr_summary.pivot(index='Protocol', columns='Network', values='Delivery_Ratio')
    pdr_summary.columns = [f'Avg_PDR_{col}' for col in pdr_summary.columns]
    
    # Combine the summaries
    summary = pd.concat([throughput_summary, latency_summary, pdr_summary], axis=1)
    
    # Save to CSV
    summary.to_csv('csv_output/protocol_summary_comparison.csv')
    
    return summary

# Execute functions
throughput_df = extract_throughput_data()
latency_df = extract_latency_data()
pdr_df = extract_pdr_data()
concurrent_df = extract_concurrent_data()

# Generate visualizations
plot_throughput_comparison(throughput_df)
plot_latency_comparison(latency_df)
plot_jitter_comparison(latency_df)
plot_pdr_comparison(pdr_df)
plot_concurrent_comparison(concurrent_df)

# Create summary
summary_df = create_summary_comparison()

print("Analysis complete! CSV files and charts have been created.")
print("\nCSV files saved in the 'csv_output' directory:")
print("  - throughput_comparison.csv")
print("  - latency_comparison.csv")
print("  - packet_delivery_ratio.csv")
print("  - concurrent_connections.csv")
print("  - protocol_summary_comparison.csv")

print("\nCharts saved in the 'charts' directory:")
print("  - throughput_comparison.png")
print("  - throughput_comparison_log.png")
print("  - latency_comparison_no_congested.png")
print("  - latency_comparison_all.png")
print("  - jitter_comparison.png")
print("  - packet_delivery_ratio.png")
print("  - pdr_congested.png")
print("  - concurrent_establishment_time.png")
print("  - concurrent_establishment_time_log.png")
print("  - rina_bandwidth_allocation.png (if applicable)")