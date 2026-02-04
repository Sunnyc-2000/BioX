import os
import re
import pandas as pd
from openpyxl.utils.exceptions import IllegalCharacterError
from collections import defaultdict


def parse_fasta_file(file_path):
    genes = []
    with open(file_path, 'r') as f:
        current_gene = None
        content = f.readlines()

        for line in content:
            if line.startswith('>'):
                if current_gene:  # 保存上一个基因信息
                    genes.append(current_gene)
                # 解析新基因
                parts = [p.strip() for p in line[1:].split(';', 3)]
                if len(parts) < 4:
                    continue

                loc_match = re.match(r'(\d+)-(\d+)', parts[1])
                if not loc_match:
                    continue

                start, end = map(int, loc_match.groups())
                gene_name = parts[3].strip()
                current_gene = {
                    'full_name': gene_name,  # 保存完整基因名
                    'start': start,
                    'end': end
                }
            else:
                # 忽略序列内容
                continue
        if current_gene:
            genes.append(current_gene)
    return genes


def clean_sheet_name(name):
    """处理非法字符并截断为31字符"""
    cleaned = re.sub(r'[\\/*?:\[\]]', '', name)
    return cleaned[:31]


def main():
    path = input("输入文件路径：").strip()
    gene_input = input("输入基因名称（支持全角/半角逗号分隔，模糊匹配）: ").strip()

    # 支持全角（，）和半角（,）逗号作为分隔符
    gene_patterns = []
    for pattern in re.split(r'[,，]', gene_input):
        cleaned_pattern = pattern.strip().lower()
        if cleaned_pattern:
            gene_patterns.append(cleaned_pattern)

    if not gene_patterns:
        print("未输入有效基因名称")
        return

    output_file = os.path.join(path, "gene_positions.xlsx")

    # 获取所有文件列表并按文件名排序
    all_files = []
    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        if os.path.isfile(file_path):
            all_files.append(filename)
    all_files.sort()  # 按文件名排序

    # 解析所有文件，缓存基因数据
    file_data = {}
    all_gene_names = set()  # 所有存在的完整基因名集合

    for filename in all_files:
        file_path = os.path.join(path, filename)
        try:
            genes_in_file = parse_fasta_file(file_path)
            file_data[filename] = genes_in_file
            for gene in genes_in_file:
                all_gene_names.add(gene['full_name'])
        except Exception as e:
            print(f"解析文件 {filename} 失败: {e}")
            file_data[filename] = []  # 保存空列表表示解析失败

    # 找到所有匹配的基因名称
    matched_genes = {}
    for full_name in all_gene_names:
        lowercase_name = full_name.lower()
        # 检查是否匹配任何输入模式
        if any(pattern in lowercase_name for pattern in gene_patterns):
            sheet_name = clean_sheet_name(full_name)
            matched_genes[full_name] = sheet_name

    if not matched_genes:
        print(f"未找到匹配的基因模式: {', '.join(gene_patterns)}")
        return

    # 为每个匹配的基因名称准备结果数据
    gene_results = defaultdict(dict)

    # 初始化每个基因在所有文件中的记录
    for gene in matched_genes:
        for filename in all_files:
            base_name = os.path.splitext(filename)[0]
            gene_results[gene][base_name] = []  # 每个文件可能有多个匹配

    # 填充结果数据
    for filename in all_files:
        base_name = os.path.splitext(filename)[0]
        genes_in_file = file_data.get(filename, [])

        # 统计每个基因在当前文件中出现的次数
        gene_count = defaultdict(int)
        for gene_data in genes_in_file:
            full_name = gene_data['full_name']
            if full_name in matched_genes:
                gene_count[full_name] += 1

        # 对于每个匹配的基因
        for gene in matched_genes:
            # 如果该文件中有此基因
            if gene in gene_count:
                # 获取此基因在该文件中的所有记录
                gene_occurrences = []
                for gene_data in genes_in_file:
                    if gene_data['full_name'] == gene:
                        gene_occurrences.append(gene_data)

                # 为每条记录创建带编号的条目
                for i, gene_data in enumerate(gene_occurrences, 1):
                    display_name = f"{base_name}-{i}" if gene_count[gene] > 1 else base_name
                    gene_results[gene][base_name].append({
                        'file_name': display_name,
                        'start': gene_data['start'],
                        'end': gene_data['end']
                    })
            else:
                # 文件中没有此基因，添加空记录
                gene_results[gene][base_name].append({
                    'file_name': base_name,
                    'start': None,
                    'end': None
                })

    # 创建Excel文件
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for full_gene_name, gene_data in gene_results.items():
            sheet_name = matched_genes[full_gene_name]

            # 准备表格数据（按文件名排序）
            all_records = []
            for base_name in sorted(gene_data.keys()):
                all_records.extend(gene_data[base_name])

            # 创建DataFrame
            df = pd.DataFrame(all_records, columns=['file_name', 'start', 'end'])

            # 确保列顺序
            df = df[['file_name', 'start', 'end']]

            try:
                # 处理可能重复的Sheet名称
                temp_sheet_name = sheet_name
                sheet_counter = 1
                while temp_sheet_name in writer.sheets:
                    temp_sheet_name = f"{sheet_name[:28]}_{sheet_counter}"  # 截断避免超长
                    sheet_counter += 1

                df.to_excel(writer, sheet_name=temp_sheet_name, index=False, header=True)
            except Exception as e:
                print(f"创建子表 {full_gene_name} 失败: {e}")

    print(f"找到 {len(matched_genes)} 个匹配的基因:")
    for gene in matched_genes.keys():
        print(f"  - {gene} (子表名: {matched_genes[gene]})")
    print(f"结果已保存至: {output_file}")


if __name__ == '__main__':
    main()