import csv

in_file = input("Name of csv to create checkpoint from: ")
urls = []
with open("checkpoint.txt", 'r', encoding="utf-8") as open_checkpoint:
    urls = open_checkpoint.read().splitlines()
with open(in_file, 'r', encoding="utf-8") as open_csv:
    reader = csv.reader(open_csv)
    for row in reader:
        url = row[0]
        if url not in urls:
            urls.append(url)

with open("checkpoint.txt", 'w', encoding="utf-8") as open_checkpoint:
    open_checkpoint.write('\n'.join(urls))