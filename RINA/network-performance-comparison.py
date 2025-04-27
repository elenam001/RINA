import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

os.makedirs('csv_output', exist_ok=True)
os.makedirs('charts', exist_ok=True)

with open('RINA/rina_metrics.json', 'r') as f:
    rina_data = json.load(f)

with open('RINA/tcp_metrics.json', 'r') as f:
    tcp_data = json.load(f)

with open('RINA/hybrid_metrics.json', 'r') as f:
    hybrid_data = json.load(f)

def extract_throughput_data():
    networks = ['perfect', 'lan', 'wifi', 'congested']
    packet_sizes = [64, 512, 1024, 4096, 8192]
    
    all_data = []
    
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
    
    for network in networks:
        for size in packet_sizes:
            if str(size) in rina_data['throughput_realistic_networks'][network]:
                row = {
                    'Protocol': 'RINA',
                    'Network': network,
                    'Packet_Size': size,
                    'Throughput_Mbps': rina_data['throughput_realistic_networks'][network][str(size)]['throughput_mbps'],
                    'Delivery_Ratio': 100.0
                }
                all_data.append(row)
    
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
    
    df = pd.DataFrame(all_data)
    df.to_csv('csv_output/throughput_comparison.csv', index=False)
    return df

def extract_latency_data():
    networks = ['perfect', 'lan', 'wifi', 'congested']
    packet_sizes = [64, 512, 1024, 4096]
    
    all_data = []
    
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
    
    df = pd.DataFrame(all_data)
    df.to_csv('csv_output/latency_comparison.csv', index=False)
    return df

def extract_detailed_scalability_data():
    connection_counts = [1, 5, 10, 25]
    all_data = []
    
    for count in [1, 5, 10, 25]:
        if str(count) in tcp_data['concurrent_tcp_connections']:
            row = {
                'Protocol': 'TCP',
                'Connection_Count': count,
                'Successful_Connections': tcp_data['concurrent_tcp_connections'][str(count)]['successful_connections'],
                'Establishment_Time_ms': tcp_data['concurrent_tcp_connections'][str(count)]['establishment_time_per_conn_ms'],
                'Success_Rate': tcp_data['concurrent_tcp_connections'][str(count)]['data_exchange_success_rate'],
                'Memory_Usage_MB': tcp_data['concurrent_tcp_connections'][str(count)].get('memory_usage_mb', None),
                'CPU_Usage_Percent': tcp_data['concurrent_tcp_connections'][str(count)].get('cpu_usage_percent', None)
            }
            all_data.append(row)
    
    networks = ['perfect', 'lan', 'wifi', 'congested']
    for network in networks:
        if network in rina_data['scalability_concurrent_flows']:
            for count in connection_counts:
                if str(count) in rina_data['scalability_concurrent_flows'][network]:
                    row = {
                        'Protocol': 'RINA',
                        'Network': network,
                        'Connection_Count': count,
                        'Successful_Connections': rina_data['scalability_concurrent_flows'][network][str(count)]['successful_flows'],
                        'Establishment_Time_ms': rina_data['scalability_concurrent_flows'][network][str(count)]['allocation_time_per_flow_ms'],
                        'Success_Rate': rina_data['scalability_concurrent_flows'][network][str(count)]['data_send_success_rate'],
                        'Bandwidth_Per_Flow_Mbps': rina_data['scalability_concurrent_flows'][network][str(count)]['bandwidth_per_flow_mbps'],
                        'Memory_Usage_MB': rina_data['scalability_concurrent_flows'][network][str(count)].get('memory_usage_mb', None),
                        'CPU_Usage_Percent': rina_data['scalability_concurrent_flows'][network][str(count)].get('cpu_usage_percent', None)
                    }
                    all_data.append(row)
    
    for count in [1, 5, 10, 25]:
        if str(count) in hybrid_data['concurrent_tcp_connections']:
            row = {
                'Protocol': 'Hybrid',
                'Connection_Count': count,
                'Successful_Connections': hybrid_data['concurrent_tcp_connections'][str(count)]['successful_connections'],
                'Establishment_Time_ms': hybrid_data['concurrent_tcp_connections'][str(count)]['establishment_time_per_conn_ms'],
                'Success_Rate': hybrid_data['concurrent_tcp_connections'][str(count)]['data_exchange_success_rate'],
                'Memory_Usage_MB': hybrid_data['concurrent_tcp_connections'][str(count)].get('memory_usage_mb', None),
                'CPU_Usage_Percent': hybrid_data['concurrent_tcp_connections'][str(count)].get('cpu_usage_percent', None)
            }
            all_data.append(row)
    
    df = pd.DataFrame(all_data)
    
    if 'Memory_Usage_MB' in df.columns and not df['Memory_Usage_MB'].isna().all():
        df['Memory_Efficiency'] = df['Successful_Connections'] / df['Memory_Usage_MB'].replace(0, float('nan'))
    
    if 'CPU_Usage_Percent' in df.columns and not df['CPU_Usage_Percent'].isna().all():
        df['CPU_Efficiency'] = df['Successful_Connections'] / df['CPU_Usage_Percent'].replace(0, float('nan'))
    
    df.to_csv('csv_output/scalability_detailed.csv', index=False)
    return df

def extract_pdr_data():
    networks = ['perfect', 'lan', 'wifi', 'congested']
    packet_sizes = [64, 1024, 4096]
    
    all_data = []
    
    for network in networks:
        for size in [64, 1024, 4096]:
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
    
    for network in networks:
        for size in [64, 1024, 4096]:
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
    
    df = pd.DataFrame(all_data)
    df.to_csv('csv_output/packet_delivery_ratio.csv', index=False)
    return df

def extract_concurrent_data():
    connection_counts = [1, 5, 10, 25]
    all_data = []
    
    for count in [1, 5, 10, 25]:
        row = {
            'Protocol': 'TCP',
            'Target_Count': count,
            'Successful_Count': tcp_data['concurrent_tcp_connections'][str(count)]['successful_connections'],
            'Establishment_Time_ms': tcp_data['concurrent_tcp_connections'][str(count)]['establishment_time_per_conn_ms'],
            'Success_Rate': tcp_data['concurrent_tcp_connections'][str(count)]['data_exchange_success_rate']
        }
        all_data.append(row)
    
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
    
    for count in [1, 5, 10, 25]:
        row = {
            'Protocol': 'Hybrid',
            'Target_Count': count,
            'Successful_Count': hybrid_data['concurrent_tcp_connections'][str(count)]['successful_connections'],
            'Establishment_Time_ms': hybrid_data['concurrent_tcp_connections'][str(count)]['establishment_time_per_conn_ms'],
            'Success_Rate': hybrid_data['concurrent_tcp_connections'][str(count)]['data_exchange_success_rate']
        }
        all_data.append(row)
    
    df = pd.DataFrame(all_data)
    df.to_csv('csv_output/concurrent_connections.csv', index=False)
    return df

def extract_rtt_data():
    networks = ['perfect', 'lan', 'wifi', 'congested']
    packet_sizes = [64, 512, 1024, 4096]
    
    all_data = []
    
    for network in networks:
        for size in packet_sizes:
            if str(size) in rina_data['round_trip_time_realistic'][network]:
                row = {
                    'Protocol': 'RINA',
                    'Network': network,
                    'Packet_Size': size,
                    'Avg_RTT_ms': rina_data['round_trip_time_realistic'][network][str(size)]['avg_rtt_ms'],
                    'Min_RTT_ms': rina_data['round_trip_time_realistic'][network][str(size)]['min_rtt_ms'],
                    'Max_RTT_ms': rina_data['round_trip_time_realistic'][network][str(size)]['max_rtt_ms']
                }
                all_data.append(row)
    
    for network in networks:
        for size in packet_sizes:
            if str(size) in tcp_data['latency_jitter_tcp'][network]:
                row = {
                    'Protocol': 'TCP',
                    'Network': network,
                    'Packet_Size': size,
                    'Avg_RTT_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['avg_rtt_ms'],
                    'Min_RTT_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['min_latency_ms'] * 2,
                    'Max_RTT_ms': tcp_data['latency_jitter_tcp'][network][str(size)]['max_latency_ms'] * 2
                }
                all_data.append(row)
    
    for network in networks:
        for size in packet_sizes:
            if str(size) in hybrid_data['latency_jitter_hybrid'][network]:
                row = {
                    'Protocol': 'Hybrid',
                    'Network': network,
                    'Packet_Size': size,
                    'Avg_RTT_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['avg_rtt_ms'],
                    'Min_RTT_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['min_latency_ms'] * 2,
                    'Max_RTT_ms': hybrid_data['latency_jitter_hybrid'][network][str(size)]['max_latency_ms'] * 2
                }
                all_data.append(row)
    
    df = pd.DataFrame(all_data)
    df.to_csv('csv_output/rtt_comparison.csv', index=False)
    return df

def plot_throughput_comparison(df):
    networks = df['Network'].unique()
    
    for network in networks:
        network_df = df[df['Network'] == network]
        
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(x='Packet_Size', y='Throughput_Mbps', hue='Protocol', 
                       data=network_df, errorbar=None, palette='viridis')
        
        ax.set_yscale('log')
        
        plt.title(f'Throughput Comparison - {network.capitalize()} Network (Log Scale)')
        plt.xlabel('Packet Size (bytes)')
        plt.ylabel('Throughput (Mbps) - Log Scale')
        plt.legend(title='Protocol')
        
        plt.tight_layout()
        plt.savefig(f'charts/throughput_{network}_network_log.png', dpi=300)
        plt.close()

def plot_jitter_comparison(df):
    plt.figure(figsize=(16, 8))
    g = sns.FacetGrid(df, col='Network', height=6, aspect=1.2)
    g.map_dataframe(sns.barplot, x='Packet_Size', y='Avg_Jitter_ms', 
                   hue='Protocol', errorbar=None, palette='Set2')
    
    g.set_axis_labels('Packet Size (bytes)', 'Average Jitter (ms)')
    g.set_titles(col_template='{col_name} Network')
    g.add_legend(title='Protocol')
    
    for ax in g.axes.flat:
        ax.grid(True, linestyle='--', alpha=0.6)
        for label in ax.get_xticklabels():
            label.set_rotation(45)
    
    plt.tight_layout()
    plt.savefig('charts/jitter_by_network_packetsize.png', dpi=300)
    
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

def plot_latency_comparison(df):
    df_no_congested = df[df['Network'] != 'congested']
    
    plt.figure(figsize=(14, 8))
    
    g = sns.FacetGrid(df_no_congested, col='Network', row='Packet_Size', height=3, aspect=1.5)
    g.map_dataframe(sns.barplot, x='Protocol', y='Avg_Latency_ms', errorbar=None, palette='cool')
    
    g.set_axis_labels('Protocol', 'Average Latency (ms)')
    g.set_titles(col_template='{col_name} Network', row_template='Packet Size: {row_name} bytes')
    
    plt.tight_layout()
    plt.savefig('charts/latency_comparison_no_congested.png', dpi=300)
    
    g = sns.FacetGrid(df, col='Network', row='Packet_Size', height=3, aspect=1.5)
    g.map_dataframe(sns.barplot, x='Protocol', y='Avg_Latency_ms', errorbar=None, palette='cool')
    
    g.set_axis_labels('Protocol', 'Average Latency (ms)')
    g.set_titles(col_template='{col_name} Network', row_template='Packet Size: {row_name} bytes')
    
    plt.tight_layout()
    plt.savefig('charts/latency_comparison_all.png', dpi=300)

def plot_pdr_comparison(df):
    plt.figure(figsize=(14, 8))
    
    g = sns.FacetGrid(df, col='Network', row='Packet_Size', height=3, aspect=1.5)
    g.map_dataframe(sns.barplot, x='Protocol', y='Delivery_Ratio', errorbar=None, palette='mako')
    
    g.set_axis_labels('Protocol', 'Packet Delivery Ratio (%)')
    g.set_titles(col_template='{col_name} Network', row_template='Packet Size: {row_name} bytes')
    
    for ax in g.axes.flat:
        ax.set_ylim(0, 105) 
    
    plt.tight_layout()
    plt.savefig('charts/packet_delivery_ratio.png', dpi=300)
    
    df_congested = df[df['Network'] == 'congested']
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_congested, x='Protocol', y='Delivery_Ratio', hue='Packet_Size', errorbar=None, palette='mako')
    plt.title('Packet Delivery Ratio in Congested Network')
    plt.ylabel('Delivery Ratio (%)')
    plt.ylim(0, 100)
    plt.legend(title='Packet Size (bytes)')
    plt.tight_layout()
    plt.savefig('charts/pdr_congested.png', dpi=300)

def plot_concurrent_comparison(df):
    plt.figure(figsize=(12, 7))
    
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

def plot_rtt_comparison(df):
    plt.figure(figsize=(16, 10))
    g = sns.FacetGrid(df, col='Network', row='Packet_Size', height=3, aspect=1.5)
    g.map_dataframe(sns.barplot, x='Protocol', y='Avg_RTT_ms', errorbar=None, palette='viridis')
    
    g.set_axis_labels('Protocol', 'Average RTT (ms)')
    g.set_titles(col_template='{col_name} Network', row_template='Packet Size: {row_name} bytes')
    
    for ax in g.axes.flat:
        ax.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig('charts/rtt_comparison_bar.png', dpi=300)
    plt.close()

def create_summary_comparison():
    throughput_df = pd.read_csv('csv_output/throughput_comparison.csv')
    latency_df = pd.read_csv('csv_output/latency_comparison.csv')
    pdr_df = pd.read_csv('csv_output/packet_delivery_ratio.csv')
    
    throughput_summary = throughput_df.groupby(['Protocol', 'Network'])['Throughput_Mbps'].mean().reset_index()
    throughput_summary = throughput_summary.pivot(index='Protocol', columns='Network', values='Throughput_Mbps')
    throughput_summary.columns = [f'Avg_Throughput_{col}' for col in throughput_summary.columns]
    
    latency_summary = latency_df.groupby(['Protocol', 'Network'])['Avg_Latency_ms'].mean().reset_index()
    latency_summary = latency_summary.pivot(index='Protocol', columns='Network', values='Avg_Latency_ms')
    latency_summary.columns = [f'Avg_Latency_{col}' for col in latency_summary.columns]
    
    pdr_summary = pdr_df.groupby(['Protocol', 'Network'])['Delivery_Ratio'].mean().reset_index()
    pdr_summary = pdr_summary.pivot(index='Protocol', columns='Network', values='Delivery_Ratio')
    pdr_summary.columns = [f'Avg_PDR_{col}' for col in pdr_summary.columns]
    
    summary = pd.concat([throughput_summary, latency_summary, pdr_summary], axis=1)
    summary.to_csv('csv_output/protocol_summary_comparison.csv')
    
    return summary

throughput_df = extract_throughput_data()
latency_df = extract_latency_data()
pdr_df = extract_pdr_data()
concurrent_df = extract_concurrent_data()
rtt_df = extract_rtt_data()
scalability_df = extract_detailed_scalability_data()

plot_throughput_comparison(throughput_df)
plot_latency_comparison(latency_df)
plot_jitter_comparison(latency_df)
plot_pdr_comparison(pdr_df)
plot_rtt_comparison(rtt_df)
plot_concurrent_comparison(concurrent_df)

summary_df = create_summary_comparison()

print("Analysis complete! CSV files and charts have been created.")