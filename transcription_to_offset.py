from waivek import Timer   # Single Use
timer = Timer()
from waivek import Code    # Multi-Use
from waivek import handler # Single Use
from waivek import ic, ib     # Multi-Use, import time: 70ms - 110ms
from waivek import rel2abs
from waivek import log

def similarity(s1: str, s2: str):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, s1, s2).ratio()

class TsvLine:
    def __init__(self, s: str):
        self.start: int
        self.end: int
        self.text: str
        start_str, end_str, self.text = s.strip().split('\t')
        self.start: int = int(start_str)
        self.end: int = int(end_str)
    # create method for tuple unpacking
    def __iter__(self):
        return iter([self.start, self.end, self.text])
    def __repr__(self):
        return "\t".join([str(self.start), str(self.end), self.text])

def remove_outliers(df, column):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

def print_similarity_information(tsvlines1, tsvlines2):
    from collections import namedtuple
    entry = namedtuple('entry', ['weight', 'value'])
    entries = []
    print_table = []
    for tsvline1 in tsvlines1:
        # sim = max([ similarity(tsvline1.text, tsvline2.text) for tsvline2 in tsvlines2 ])
        # select the tsvline2 with the highest similarity

        sim, tsvline2 = max([ (similarity(tsvline1.text, tsvline2.text), tsvline2) for tsvline2 in tsvlines2 ], key=lambda x: x[0])
        difference = tsvline1.start - tsvline2.start
        difference_seconds = difference / 1000
        # print(f"{sim:.2f}\t{difference_seconds:.2f}\t{tsvline1.text}")
        entries.append(entry(weight=sim, value=difference_seconds))
        print_table.append({ 'similarity': float("%.2f" % sim), 'difference_seconds': difference_seconds, 'text': tsvline1.text })

    # remove print_table where similarity < 0.9
    # print_table = [ row for row in print_table if row['similarity'] >= 0.9 ]
    # print_table.sort(key=lambda x: x['similarity'], reverse=True)
    ic(print_table)

    import pandas as pd
    import numpy as np
    df = pd.DataFrame(entries)
    df = remove_outliers(df, 'value')
    weights = df['weight'] / df['weight'].sum()

    # Calculate weighted average of difference_seconds
    weighted_offset = np.average(df['value'], weights=weights)
    weighted_offset_string = "%.2f" % weighted_offset
    ic(weighted_offset_string)

    return weighted_offset


def do_transcription_sync(filepath1, filepath2):
    with open(filepath1, 'r') as f1, open(filepath2, 'r') as f2:
        lines1 = [ line.strip() for line in f1.readlines() ][1:]
        lines2 = [ line.strip() for line in f2.readlines() ][1:]
    tsvlines1 = [ TsvLine(line) for line in lines1 ]
    tsvlines2 = [ TsvLine(line) for line in lines2 ]
    # results: list[tuple[float, TsvLine, TsvLine]] = []
    # for tsvline1 in tsvlines1:
    #     for tsvline2 in tsvlines2:
    #         sim = similarity(tsvline1.text, tsvline2.text)
    #         results.append((sim, tsvline1, tsvline2))
    # results.sort(key=lambda x: x[0], reverse=True)
    # table = [ { "sim": "%.2f" % sim, "tsvline1": tsvline1.text, "tsvline2": tsvline2.text } for sim, tsvline1, tsvline2 in results ]
    # ic(table)

    # for tsvline1 in tsvlines1:
    #     sim1 = max([ similarity(tsvline1.text, tsvline2.text) for tsvline2 in tsvlines2 ])
    #     print(f"{sim1:.2f}\t{tsvline1.text}")

    print_similarity_information(tsvlines1, tsvlines2)

def main():
    filepath1 = "/home/vivek/hateoas/static/downloads/transcriptions/2199687421_01h28m08s_120s.tsv"
    filepath2 = "/home/vivek/hateoas/static/downloads/transcriptions/2199424572_06h52m18s_120s.tsv"
    filepath1 = "2199687421_01h28m08s_120s.tsv"
    filepath2 = "2199424572_06h52m18s_120s.tsv"
    
    filepath1 = "/home/vivek/hateoas/static/downloads/transcriptions/2198842566_00h18m21s_120s.tsv"
    filepath2 = "/home/vivek/hateoas/static/downloads/transcriptions/2198727507_02h44m10s_120s.tsv"
    log("")
    do_transcription_sync(filepath2, filepath1)
    do_transcription_sync(filepath1, filepath2)

if __name__ == "__main__":
    with handler():
        main()

