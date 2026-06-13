import pandas as pd

df = pd.read_json("training_data.jsonl", lines=True)

df.to_excel("training_dataset.xlsx", index=False)

print("Excel file created successfully!")