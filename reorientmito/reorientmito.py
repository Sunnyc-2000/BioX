import os
import pandas as pd
import glob
import shutil
from datetime import datetime


def read_fasta(file_path):
    """读取FASTA文件，处理可能的多行序列"""
    with open(file_path, 'r') as f:
        header = f.readline().strip()
        sequence = ''.join(line.strip() for line in f)
    return header, sequence


def write_fasta(file_path, header, sequence, line_length=80):
    """写入FASTA文件，每行限制指定长度"""
    with open(file_path, 'w') as f:
        f.write(header + '\n')
        # 将长序列分割为多行
        for i in range(0, len(sequence), line_length):
            f.write(sequence[i:i + line_length] + '\n')


def adjust_sequence_and_header(input_path, output_path, new_start=None, expected_header=None):
    """调整序列起始点和/或标题行"""
    header, sequence = read_fasta(input_path)

    header_correction = None
    # 修正标题行（如果提供了预期的标题）
    if expected_header:
        if header != expected_header:
            header_correction = f"Header corrected: '{header}' -> '{expected_header}'"
            header = expected_header

    # 调整起始位点（如果提供了新的起始点）
    sequence_adjustment = None
    if new_start is not None:
        n = len(sequence)
        # 处理超出范围的起始位点
        adjusted_start = (int(new_start) - 1) % n
        new_sequence = sequence[adjusted_start:] + sequence[:adjusted_start]
        sequence_adjustment = f"Sequence start adjusted from 1 to position {new_start}"
        sequence = new_sequence

    # 写入新文件
    write_fasta(output_path, header, sequence)

    return header_correction, sequence_adjustment


def header_only_mode(fasta_dir):
    """模式1：仅根据文件名修改标题行"""
    # 创建结果文件夹
    results_dir = os.path.join(fasta_dir, "模式1结果")
    os.makedirs(results_dir, exist_ok=True)

    fasta_files = glob.glob(os.path.join(fasta_dir, '*.*'))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    log_file = os.path.join(results_dir, f"{timestamp}_header_correction_log.txt")

    processed_files = []
    corrected_headers = []
    skipped_files = []

    for file_path in fasta_files:
        filename = os.path.basename(file_path)

        # 跳过日志文件、结果文件夹和特殊文件
        if (filename.startswith(('.', '_')) or
                os.path.isdir(file_path) or
                filename.endswith(('.log', '.txt', '.xlsx', '.xls'))):
            skipped_files.append(filename)
            continue

        # 获取基础文件名（不带扩展名）
        base_name, ext = os.path.splitext(filename)

        # 检查是否是FASTA文件
        if ext.lower() not in ['.fas', '.fasta', '.fa', '.fna']:
            skipped_files.append(filename)
            continue

        # 预期的标题行
        expected_header = f">{base_name}"

        # 读取文件
        try:
            header, sequence = read_fasta(file_path)
        except Exception as e:
            print(f"读取文件 {filename} 出错: {e}")
            skipped_files.append(filename)
            continue

        # 检查是否需要修正标题行
        if header != expected_header:
            # 输出路径保持原文件名
            output_path = os.path.join(results_dir, filename)
            # 仅修正标题行，不修改序列
            try:
                write_fasta(output_path, expected_header, sequence)
                processed_files.append(filename)
                corrected_headers.append(f"{filename}: '{header}' -> '{expected_header}'")
            except Exception as e:
                print(f"写入文件 {output_path} 出错: {e}")

    # 写入日志
    with open(log_file, 'w') as log:
        log.write(f"标题修正日志 - {timestamp}\n\n")
        log.write(f"结果文件夹: {results_dir}\n")
        log.write(f"成功修正 {len(processed_files)} 个文件的标题行:\n")
        for name in processed_files:
            log.write(f" - {name}\n")

        if corrected_headers:
            log.write("\n修正详情:\n")
            for note in corrected_headers:
                log.write(f" - {note}\n")

        if skipped_files:
            log.write("\n跳过的文件(非FASTA文件或其他特殊文件):\n")
            for name in skipped_files:
                log.write(f" - {name}\n")

    return processed_files, results_dir


def full_processing_mode(fasta_dir, excel_path):
    """模式2：完整处理（Excel中的标题修正和起始位点调整）"""
    # 创建结果文件夹
    results_dir = os.path.join(fasta_dir, "模式2结果")
    os.makedirs(results_dir, exist_ok=True)

    # 读取Excel文件并处理列名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    log_file = os.path.join(results_dir, f"{timestamp}_full_processing_log.txt")

    name_to_start = {}
    excel_error = False

    # 尝试读取Excel文件
    try:
        # 自动检测Excel引擎
        if excel_path.endswith('.xlsx'):
            engine = 'openpyxl'
        else:  # 包括.xls和其他格式
            engine = 'xlrd'

        df = pd.read_excel(excel_path, engine=engine)

        # 列名映射：兼容多种可能名称
        name_column = None
        start_column = None

        # 识别列名
        for col in df.columns:
            col_lower = col.lower()
            if any(key in col_lower for key in ['file', 'name', '序列名称', '样本', 'id']):
                name_column = col
            if any(key in col_lower for key in ['start', 'begin', '起始', '位点', 'position']):
                start_column = col

        # 如果无法识别列名，使用前两列
        if not name_column or not start_column:
            if len(df.columns) >= 2:
                name_column = df.columns[0]
                start_column = df.columns[1]
                print(f"警告：使用默认列名: {name_column} 和 {start_column}")
            else:
                raise ValueError("Excel文件列数不足，需要至少两列数据")

        # 创建映射字典
        for i, (_, row) in enumerate(df.iterrows()):
            try:
                raw_name = str(row[name_column])
                clean_name = os.path.splitext(raw_name)[0]

                # 确保开始位置是整数
                start_pos = int(row[start_column])

                name_to_start[clean_name] = start_pos
            except Exception as e:
                print(f"处理第 {i + 1} 行时出错: {e}")
                print(f"行内容: {row}")

    except ImportError as e:
        # 处理依赖缺失问题
        error_msg = f"Excel读取错误: {e}\n\n请安装必需的Excel支持库："
        if 'xlrd' in str(e):
            error_msg += "\n  pip install xlrd"
        elif 'openpyxl' in str(e):
            error_msg += "\n  pip install openpyxl"
        else:
            error_msg += f"\n  pip install xlrd openpyxl"

        print(error_msg)
        excel_error = True

        # 写入错误日志
        with open(log_file, 'w') as log:
            log.write(f"完整处理日志 - {timestamp}\n\n")
            log.write("错误: 无法读取Excel文件\n")
            log.write(error_msg)

        return [], results_dir

    except Exception as e:
        print(f"读取Excel文件出错: {e}")
        excel_error = True

        # 写入错误日志
        with open(log_file, 'w') as log:
            log.write(f"完整处理日志 - {timestamp}\n\n")
            log.write("错误: 无法读取Excel文件\n")
            log.write(str(e))

        return [], results_dir

    # 获取所有基因序列文件
    fasta_files = glob.glob(os.path.join(fasta_dir, '*.*'))
    # 只保留FASTA扩展名的文件
    fasta_files = [f for f in fasta_files
                   if os.path.splitext(f)[1].lower() in ['.fas', '.fasta', '.fa', '.fna']]

    # 获取所有FASTA文件的基名
    all_fasta_basenames = {os.path.splitext(os.path.basename(f))[0] for f in fasta_files}

    processed_files = []
    missing_in_fasta = []
    corrected_headers = []
    adjusted_sequences = []

    # 处理每个序列
    for base_name, start_pos in name_to_start.items():
        # 查找匹配的文件
        matched_files = [f for f in fasta_files
                         if os.path.splitext(os.path.basename(f))[0] == base_name]

        if not matched_files:
            missing_in_fasta.append(base_name)
            continue

        input_path = matched_files[0]
        filename = os.path.basename(input_path)
        output_path = os.path.join(results_dir, filename)  # 保持原始文件名
        expected_header = f">{base_name}"

        try:
            # 调整序列并记录结果
            header_correction, sequence_adjustment = adjust_sequence_and_header(
                input_path, output_path, new_start=start_pos, expected_header=expected_header
            )

            processed_files.append(filename)

            if header_correction:
                corrected_headers.append(header_correction)
            if sequence_adjustment:
                adjusted_sequences.append(sequence_adjustment)
        except Exception as e:
            print(f"处理文件 {filename} 时出错: {e}")
            # 如果出错，可能创建了不完整的输出文件，尝试删除
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass

    # 查找FASTA文件夹中有但Excel中没有的序列
    excel_names = set(name_to_start.keys())
    missing_in_excel = list(all_fasta_basenames - excel_names)

    # 写入日志
    with open(log_file, 'w') as log:
        log.write(f"完整处理日志 - {timestamp}\n\n")
        log.write(f"结果文件夹: {results_dir}\n")
        log.write(f"源Excel文件: {os.path.basename(excel_path)}\n")

        if excel_error:
            log.write("错误: 无法读取Excel文件\n")
            return [], results_dir

        log.write(f"列名映射:\n")
        log.write(f"  文件名: '{name_column}'\n")
        log.write(f"  起始位点: '{start_column}'\n\n")

        log.write(f"成功处理 {len(processed_files)} 个文件:\n")
        log.write('\n'.join(f" - {name}" for name in processed_files) + '\n\n')

        if corrected_headers:
            log.write("修正的标题行:\n")
            log.write('\n'.join(f" - {note}" for note in corrected_headers) + '\n\n')

        if adjusted_sequences:
            log.write("序列起始点调整:\n")
            log.write('\n'.join(f" - {note}" for note in adjusted_sequences) + '\n\n')

        if missing_in_fasta:
            log.write(f"Excel中有但FASTA文件夹中未找到 ({len(missing_in_fasta)}):\n")
            log.write('\n'.join(f" - {name}" for name in missing_in_fasta) + '\n\n')

        if missing_in_excel:
            log.write(f"FASTA文件夹中有但Excel中未列出 ({len(missing_in_excel)}):\n")
            log.write('\n'.join(f" - {name}" for name in missing_in_excel) + '\n\n')

    return processed_files, results_dir


def main():
    print("基因序列起始位点调整工具")
    print("=" * 50)
    print("请选择运行模式:")
    print("1: 仅修改标题行（根据文件名）")
    print("2: 完整处理（读取Excel，修改标题和调整起始位点）")
    print("=" * 50)

    mode = input("请输入选择的模式编号(1或2): ").strip()

    fasta_directory = input("请输入FASTA文件(fas、fasta、fna、faa类型的文件都可)目录路径: ").strip()

    if mode == "1":
        print("\n运行模式: 仅修正标题行")
        print("正在处理文件...")
        try:
            processed, results_dir = header_only_mode(fasta_directory)
            print(f"\n成功处理 {len(processed)} 个文件!")
            print(f"结果文件保存在: {results_dir}")
        except Exception as e:
            print(f"\n处理过程中出错: {e}")
    elif mode == "2":
        print("\n运行模式: 完整处理（标题+起始位点）")
        excel_file_path = input("请输入Excel文件路径: ").strip()
        print("正在处理文件...")
        try:
            processed, results_dir = full_processing_mode(fasta_directory, excel_file_path)
            if processed:
                print(f"\n成功处理 {len(processed)} 个文件!")
            else:
                print("\n没有成功处理的文件，请检查日志了解详情")
            print(f"结果文件保存在: {results_dir}")
        except Exception as e:
            print(f"\n处理过程中出错: {e}")
    else:
        print("错误: 无效的模式选择! 请选择1或2。")


if __name__ == "__main__":
    main()