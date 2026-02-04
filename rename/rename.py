import os
import csv
import time
import logging
from datetime import datetime, timedelta
import re


def normalize_path(path):
    """统一路径分隔符为当前操作系统的格式"""
    return os.path.normpath(path)


def validate_and_create_path(path, is_log_path=False):
    """验证路径是否存在，不存在时根据类型处理"""
    try:
        path = normalize_path(path)
        if not os.path.exists(path):
            if is_log_path:
                os.makedirs(path)
                return path, True
            else:
                return None, False
        return path, True
    except Exception as e:
        print(f"路径处理错误: {e}")
        return None, False


def setup_logging(log_dir):
    """配置日志系统"""
    try:
        log_dir, is_valid = validate_and_create_path(log_dir, is_log_path=True)
        if not is_valid:
            return None

        log_filename = f"rename_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = os.path.join(log_dir, log_filename)

        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 添加控制台输出
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        console.setFormatter(formatter)
        logging.getLogger().addHandler(console)

        return log_path
    except Exception as e:
        print(f"日志初始化失败: {e}")
        return None


def parse_csv_mapping(csv_path):
    """解析CSV文件构建映射字典"""
    mapping = {}
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # 跳过标题行

            for row in reader:
                if len(row) >= 2:
                    original = row[0].strip()
                    new_name = row[1].strip()
                    mapping[original] = new_name
        return mapping, True
    except Exception as e:
        logging.error(f"CSV文件解析失败: {e}")
        return {}, False


def rename_files_and_dirs(directory, mapping, log_dir):
    """执行文件/文件夹重命名操作"""
    start_time = time.time()
    logging.info(f"开始重命名操作 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 统计相关变量
    renamed_count = 0
    total_items = 0
    unmatched_csv = set(mapping.keys())
    unmatched_files = []
    duplicate_names = {}
    multi_type_matches = {}

    # 收集目标目录中的所有项
    all_items = []
    try:
        for item in os.listdir(directory):
            full_path = os.path.join(directory, item)
            if os.path.isfile(full_path):
                item_type = "文件"
                base_name, ext = os.path.splitext(item)
                all_items.append((item, base_name, ext, item_type, full_path))
            elif os.path.isdir(full_path):
                item_type = "文件夹"
                all_items.append((item, item, "", item_type, full_path))
            total_items += 1
    except Exception as e:
        logging.error(f"目录访问失败: {e}")
        return

    # 准备重命名操作并收集统计信息
    rename_operations = []
    for item, base_name, ext, item_type, full_path in all_items:
        if base_name in mapping:
            # 更新统计信息
            unmatched_csv.discard(base_name)

            new_base = mapping[base_name]
            new_full = new_base + ext if ext else new_base
            new_path = os.path.join(directory, new_full)

            # 记录多类型匹配
            if base_name not in multi_type_matches:
                multi_type_matches[base_name] = []
            multi_type_matches[base_name].append((item, item_type))

            # 检查目标是否已存在
            if os.path.exists(new_path):
                if new_full not in duplicate_names:
                    duplicate_names[new_full] = []
                duplicate_names[new_full].append(full_path)

            # 添加重命名操作
            rename_operations.append((full_path, new_path, item, new_full, item_type))

    # 查找未匹配项
    for item, base_name, _, item_type, _ in all_items:
        if base_name not in mapping:
            unmatched_files.append((item, item_type))

    # 执行实际的重命名
    for src_path, dst_path, orig_name, new_name, item_type in rename_operations:
        if os.path.exists(dst_path):
            logging.warning(f"跳过重命名！目标已存在: {orig_name} -> {new_name} ({item_type})")
            continue

        try:
            os.rename(src_path, dst_path)
            renamed_count += 1
            logging.info(f"已重命名: {orig_name} -> {new_name} ({item_type})")
        except Exception as e:
            logging.error(f"重命名失败: {orig_name} -> {new_name} | 错误: {e}")

    # 记录各种特殊情况
    if unmatched_csv:
        logging.warning("CSV中有但文件夹中未找到的项:")
        for item in unmatched_csv:
            logging.warning(f"  - {item}")

    if unmatched_files:
        logging.warning("文件夹中有但CSV中未找到的项:")
        for item, item_type in unmatched_files:
            logging.warning(f"  - {item} ({item_type})")

    if duplicate_names:
        logging.warning("重名冲突项:")
        for name, paths in duplicate_names.items():
            logging.warning(f"  - {name} 出现在:")
            for path in paths:
                logging.warning(f"      {os.path.basename(path)}")

    # 记录多类型匹配
    multi_type_count = 0
    for base_name, matches in multi_type_matches.items():
        if len(matches) > 1:
            types = set(match[1] for match in matches)
            if len(types) > 1:
                multi_type_count += 1
                logging.warning(f"重复匹配警告: '{base_name}' 匹配了多种类型:")
                for match in matches:
                    logging.warning(f"  - {match[0]} ({match[1]})")

    # 最终统计
    end_time = time.time()
    elapsed = timedelta(seconds=end_time - start_time)

    logging.info(f"\n{'=' * 40} 操作总结 {'=' * 40}")
    logging.info(f"总处理项: {total_items} | 成功重命名: {renamed_count}")
    logging.info(f"无匹配文件/文件夹: {len(unmatched_files)}")
    logging.info(f"CSV中未使用的项: {len(unmatched_csv)}")
    logging.info(f"重名冲突: {len(duplicate_names)}")
    logging.info(f"多类型匹配项: {multi_type_count}")
    logging.info(f"开始时间: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"结束时间: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"总耗时: {elapsed}")


def main():
    print("=" * 50)
    print("文件/文件夹重命名工具")
    print("=" * 50)
    print("\n请提供以下路径信息：")

    # 获取用户输入并规范化路径
    csv_path = input("1. CSV文件路径: ")
    directory = input("2. 待处理的文件夹路径: ")
    log_dir = input("3. 日志输出目录: ")

    # 标准化路径
    csv_path = normalize_path(csv_path)
    directory = normalize_path(directory)
    log_dir = normalize_path(log_dir)

    # 验证路径
    csv_valid = os.path.isfile(csv_path)
    dir_valid = os.path.isdir(directory)

    if not csv_valid:
        print(f"错误: CSV文件不存在 [{csv_path}]")
        return
    if not dir_valid:
        print(f"错误: 目录不存在 [{directory}]")
        return

    # 设置日志
    log_path = setup_logging(log_dir)
    if not log_path:
        print("错误: 无法初始化日志系统")
        return

    print(f"\n开始处理... 查看详细日志请访问: {log_path}")

    # 解析CSV映射
    mapping, success = parse_csv_mapping(csv_path)
    if not success:
        print("CSV解析失败，请检查日志")
        return

    # 执行重命名操作
    rename_files_and_dirs(directory, mapping, log_dir)
    print("\n操作完成！请查看日志文件获取详细信息")


if __name__ == "__main__":
    main()