import os

# Your folder path
folder_path = r"D:\Thiru\aerolinkers-sw"

# Output file name
output_file = os.path.join(folder_path, "file_list.txt")

with open(output_file, "w") as f:
    for file in os.listdir(folder_path):
        f.write(file + "\n")

print("✅ File names saved to:", output_file)