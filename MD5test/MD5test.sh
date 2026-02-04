#!/bin/bash

# 记录开始时间
start_time=$(date +%s)
start_time_readable=$(date '+%Y-%m-%d %H:%M:%S')

# 进度显示函数
show_progress() {
    local current_time=$(date +%s)
    local elapsed=$((current_time - start_time))
    printf "\r已运行: %02d:%02d:%02d | %s" \
        $((elapsed/3600)) $(((elapsed%3600)/60)) $((elapsed%60)) \
        "$1"
}

# 选择模式
echo "请选择运行模式:"
echo "1) 仅计算MD5值（不进行验证）"
echo "2) 完整验证（计算并比对MD5值）"
read -p "请输入选项编号 (1或2): " run_mode

if [[ "$run_mode" != "1" && "$run_mode" != "2" ]]; then
    echo "错误：无效选项，请重新运行并输入1或2"
    exit 1
fi

# 输入路径和文件名
read -p "请输入存放文件的目录路径: " file_dir
read -p "请输入新生成MD5值的存储文件名: " new_md5_file

if [ "$run_mode" == "2" ]; then
    read -p "请输入已知MD5值存储文件的完整路径: " original_md5_file
    read -p "请输入比对报告文件名: " report_file
fi

# 检查目录是否存在
if [ ! -d "$file_dir" ]; then
    echo "错误：文件目录不存在！"
    exit 1
fi

if [ "$run_mode" == "2" ] && [ ! -f "$original_md5_file" ]; then
    echo "错误：已知MD5文件不存在！"
    exit 1
fi

# 进入目录计算MD5值
cd "$file_dir" || exit

echo "正在计算文件MD5值，请稍候..."
show_progress "开始计算"

file_count=0
total_files=$(find . -maxdepth 1 -type f | wc -l)

# 计算MD5值
for file in *; do
    if [ -f "$file" ]; then
        ((file_count++))
        show_progress "计算中 ($file_count/$total_files): $file"
        md5sum "$file" >> temp_md5_file
    fi
done

# 处理临时MD5文件，去掉路径前缀
awk '{
    if (index($2, "./") == 1) {
        $2 = substr($2, 3);
    }
    print $1, $2;
}' temp_md5_file > "$new_md5_file"
rm -f temp_md5_file

show_progress "完成MD5计算"
echo -e "\n\n成功提取 $file_count 个文件的MD5值"
echo "新MD5值文件: $(pwd)/$new_md5_file"

# 如果选择的是仅计算模式，则直接退出
if [ "$run_mode" == "1" ]; then
    end_time=$(date +%s)
    elapsed_time=$((end_time - start_time))
    printf "总耗时: %02d:%02d:%02d\n" $((elapsed_time/3600)) $(((elapsed_time%3600)/60)) $((elapsed_time%60))
    exit 0
fi

# 完整验证模式
echo "开始验证MD5值，请稍候..."
show_progress "开始验证"

# 初始化各类文件列表
consistent_files=()
inconsistent_files=()
missing_files=()
new_files=()

# 创建关联数组存储已知MD5值
declare -A original_md5_map

# 读取原始MD5文件
original_count=0
while IFS= read -r line; do
    if [[ -z "$line" ]]; then continue; fi
    original_md5=$(echo "$line" | awk '{print $1}')
    original_name=$(echo "$line" | awk '{$1=""; print substr($0,2)}')
    original_name=${original_name## }  # 去除前导空格
    
    if [[ ! "$original_md5" =~ ^[a-f0-9]{32}$ ]] || [ -z "$original_name" ]; then
        continue
    fi
    
    original_md5_map["$original_name"]="$original_md5"
    ((original_count++))
    show_progress "读取MD5记录 $original_count"
done < "$original_md5_file"

# 开始对比
verified_count=0
total_to_verify=$(wc -l < "$new_md5_file")

# 处理新提取的MD5值
while IFS= read -r line; do
    ((verified_count++))
    if [[ -z "$line" ]]; then continue; fi
    new_md5=$(echo "$line" | awk '{print $1}')
    filename=$(echo "$line" | awk '{$1=""; print substr($0,2)}')
    filename=${filename## }  # 去除前导空格
    
    show_progress "验证中 ($verified_count/$total_to_verify)"
    
    # 检查是否在原始MD5中存在
    if [ -z "${original_md5_map[$filename]}" ]; then
        new_files+=("$filename")
        continue
    fi
    
    if [ "$new_md5" == "${original_md5_map[$filename]}" ]; then
        consistent_files+=("$filename")
    else
        inconsistent_files+=("$filename")
    fi
    
    # 从原始MD5映射中移除已处理的文件
    unset original_md5_map["$filename"]
done < "$new_md5_file"

# 剩余未匹配的文件就是缺失的文件
missing_files=("${!original_md5_map[@]}")

# 记录结束时间
end_time=$(date +%s)
end_time_readable=$(date '+%Y-%m-%d %H:%M:%S')
elapsed_time=$((end_time - start_time))

# 生成报告文件
{
    echo "MD5值比对详细报告"
    echo "================================"
    echo "开始时间: $start_time_readable"
    echo "结束时间: $end_time_readable"
    printf "共执行时间: %02d:%02d:%02d\n" $((elapsed_time/3600)) $(((elapsed_time%3600)/60)) $((elapsed_time%60))
    echo "目录位置: $file_dir"
    echo "提取文件数量: $file_count"
    echo "原始MD5记录数: $original_count"
    echo "------------------------------"
    
    echo ""
    echo "===== 文件状态统计 ====="
    echo "匹配文件数: ${#consistent_files[@]}"
    echo "不匹配文件数: ${#inconsistent_files[@]}"
    echo "缺失文件数: ${#missing_files[@]}"
    echo "新增文件数: ${#new_files[@]}"
    echo "------------------------------"
    
    echo ""
    echo "===== 匹配文件 (${#consistent_files[@]}) ====="
    printf "%-40s %s\n" "文件名" "MD5值"
    for file in "${consistent_files[@]}"; do
        printf "%-40s %s\n" "$file" "${original_md5_map[$file]}"
    done
    
    echo ""
    echo "===== 不匹配文件 (${#inconsistent_files[@]}) ====="
    printf "%-40s %-40s %s\n" "文件名" "已知MD5" "计算MD5"
    for file in "${inconsistent_files[@]}"; do
        printf "%-40s %-40s %s\n" "$file" "${original_md5_map[$file]}" "$(grep " $file$" "$new_md5_file" | awk '{print $1}')"
    done
    
    echo ""
    echo "===== 缺失文件 (${#missing_files[@]}) ====="
    echo "注意：这些文件在已知MD5列表中有记录，但未在当前目录中找到"
    printf "%-40s %s\n" "文件名" "MD5值"
    for file in "${missing_files[@]}"; do
        printf "%-40s %s\n" "$file" "${original_md5_map[$file]}"
    done
    
    echo ""
    echo "===== 新增文件 (${#new_files[@]}) ====="
    echo "注意：这些文件存在于当前目录中，但已知MD5列表中没有记录"
    printf "%-40s %s\n" "文件名" "计算MD5"
    for file in "${new_files[@]}"; do
        printf "%-40s %s\n" "$file" "$(grep " $file$" "$new_md5_file" | awk '{print $1}')"
    done
} > "$report_file"

show_progress "验证完成"
echo -e "\n\n比对报告已生成: $(pwd)/$report_file"
printf "总耗时: %02d:%02d:%02d\n" $((elapsed_time/3600)) $(((elapsed_time%3600)/60)) $((elapsed_time%60))
