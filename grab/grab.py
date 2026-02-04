import os
import sys


def process_fasta_file(input_path, output_path):
    sequences = []
    current_header = None
    current_seq = []

    try:
        with open(input_path, 'r') as file:
            for line in file:
                line = line.strip()
                if line.startswith('>'):
                    if current_header is not None:
                        seq_str = ''.join(current_seq)
                        sequences.append((current_header, seq_str))
                        current_seq = []
                    current_header = line
                else:
                    current_seq.append(line)

            if current_header is not None:
                seq_str = ''.join(current_seq)
                sequences.append((current_header, seq_str))
    except Exception as e:
        print(f"读取文件时出错: {str(e)}")
        return False

    if not sequences:
        print("错误: 文件中未找到有效序列")
        return False

    try:
        first_len = len(sequences[0][1])
        for header, seq in sequences:
            seq_len = len(seq)
            if seq_len != first_len:
                print(f"错误: 序列长度不一致。首序列长度: {first_len}, 序列 '{header[1:].split()[0]}' 长度: {seq_len}")
                return False
            if seq_len % 3 != 0:
                print(f"错误: 序列长度不是3的倍数。序列 '{header[1:].split()[0]}' 长度: {seq_len}")
                return False

        processed_sequences = []
        for header, seq in sequences:
            new_seq = ''.join([seq[i:i + 2] for i in range(0, len(seq), 3)])
            processed_sequences.append((header, new_seq))

        with open(output_path, 'w') as out_file:
            for header, seq in processed_sequences:
                out_file.write(f"{header}\n")
                for i in range(0, len(seq), 60):
                    out_file.write(seq[i:i + 60] + "\n")

        return True
    except Exception as e:
        print(f"处理序列时出错: {str(e)}")
        return False


def main():
    # 打印使用说明
    print("""
FASTA序列处理工具 - 每三个碱基提取前两位

使用说明：
1. 输入FASTA文件路径：处理单个文件，输出为同目录下的out12.fas
2. 输入文件夹路径：处理目录下所有.fas和.fasta文件
   每个文件生成对应的_filename_out12.fas

示例：
    输入文件：data/sample.fas 
        输出：data/out12.fas
    输入文件夹：data/sequences
        输出：data/sequences/sample1_out12.fas
              data/sequences/sample2_out12.fas

重要：所有序列必须是等长且长度为3的倍数
""")

    while True:
        path = input("\n请输入FASTA文件或文件夹路径 (输入 'q' 退出): ").strip()

        if path.lower() == 'q':
            print("程序已退出")
            sys.exit(0)

        if not os.path.exists(path):
            print(f"错误: 路径不存在 - {path}")
            continue

        if os.path.isfile(path):
            output_file = os.path.join(os.path.dirname(path), "out12.fas")
            print(f"处理单个文件: {os.path.basename(path)}")

            if process_fasta_file(path, output_file):
                print(f"处理完成! 结果保存至: {output_file}")

        elif os.path.isdir(path):
            print(f"处理文件夹: {path}")
            processed_count = 0
            error_count = 0

            for filename in os.listdir(path):
                if filename.endswith((".fas", ".fasta")):
                    input_file = os.path.join(path, filename)
                    # 创建带原始文件名的输出文件 (保留原文件名)
                    base_name = os.path.splitext(filename)[0]
                    output_file = os.path.join(path, f"{base_name}_out12.fas")

                    print(f"处理文件: {filename}", end="... ")
                    if process_fasta_file(input_file, output_file):
                        print("成功")
                        processed_count += 1
                    else:
                        print("失败")
                        error_count += 1

            print(f"\n处理完成! 成功: {processed_count} 个文件, 失败: {error_count} 个文件")


if __name__ == "__main__":
    main()