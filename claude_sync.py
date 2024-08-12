import pandas as pd
import numpy as np
from scipy.signal import correlate

def load_transcripts(file1, file2):
    df1 = pd.read_csv(file1, sep='\t', names=['start', 'end', 'text'])
    df2 = pd.read_csv(file2, sep='\t', names=['start', 'end', 'text'])

    # Convert 'start' and 'end' columns to numeric, then to seconds
    for df in [df1, df2]:
        df['start'] = pd.to_numeric(df['start'], errors='coerce') / 1000
        df['end'] = pd.to_numeric(df['end'], errors='coerce') / 1000
        # Remove rows with NaN values
        df.dropna(subset=['start', 'end'], inplace=True)

    return df1, df2

def create_text_signal(df, total_duration, step=0.1):
    signal = np.zeros(int(total_duration / step))
    for _, row in df.iterrows():
        start_idx = max(0, int(row['start'] / step))
        end_idx = min(int(row['end'] / step), len(signal))
        if start_idx < end_idx:
            signal[start_idx:end_idx] = 1
    return signal

def find_best_alignment(df1, df2, total_duration, step=0.1):
    signal1 = create_text_signal(df1, total_duration, step)
    signal2 = create_text_signal(df2, total_duration, step)

    correlation = correlate(signal1, signal2, mode='full')
    lags = np.arange(-len(signal2) + 1, len(signal1))
    best_lag = lags[np.argmax(correlation)]

    return best_lag * step

def calculate_offset(df1, df2, alignment_offset):
    # Get the first valid start time from each dataframe
    start1 = df1['start'].min()
    start2 = df2['start'].min()

    # Calculate the offset
    file_offset = start2 - start1
    total_offset = file_offset + alignment_offset

    return total_offset

def main():
    file1 = "/home/vivek/hateoas/static/downloads/transcriptions/2199687421_01h28m08s_120s.tsv"
    file2 = "/home/vivek/hateoas/static/downloads/transcriptions/2199424572_06h52m18s_120s.tsv"
    total_duration = 120  # 120 seconds

    df1, df2 = load_transcripts(file1, file2)
    alignment_offset = find_best_alignment(df1, df2, total_duration)
    total_offset = calculate_offset(df1, df2, alignment_offset)

    print(f"{total_offset:.3f}")

if __name__ == "__main__":
    main()
