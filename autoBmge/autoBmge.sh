#!/bin/bash

# 交互式输入设置
read -p "请输入文件输入路径: " input_directory
read -p "请输入文件输出路径: " output_directory
read -p "是否修改其它参数? (Y/N): " modify_params

# 设置默认参数
matrix="BLOSUM95"   # 默认矩阵参数
gap_cutoff="0.2"    # 默认gap阈值
bmge_jar="/home/insect303/tools/BMGE.jar"  # 固定路径

# 处理参数修改请求
if [[ "$modify_params" =~ ^[Yy]$ ]]; then
    echo "请选择BLOSUM矩阵参数："
    echo "1. 亲缘关系较近 (BLOSUM95)"
    echo "2. 亲缘关系较远 (BLOSUM30)"
    echo "3. 默认关系 (BLOSUM62)"
    echo "4. 手动输入其他矩阵"
    
    read -p "请选择 [1-4]: " matrix_choice
    case $matrix_choice in
        1) matrix="BLOSUM95" ;;
        2) matrix="BLOSUM30" ;;
        3) matrix="BLOSUM62" ;;
        4) read -p "请输入矩阵名称 (如BLOSUM50): " matrix ;;
        *) echo "无效选择，使用默认BLOSUM95"; matrix="BLOSUM95" ;;
    esac

    read -p "修改gap阈值? (当前:$gap_cutoff 输入新值或直接回车跳过): " new_gap
    [[ -n "$new_gap" ]] && gap_cutoff="$new_gap"
fi

# 显示配置信息
echo -e "\n配置信息:"
echo "输入目录: $input_directory"
echo "输出目录: $output_directory"
echo "矩阵参数: $matrix"
echo "Gap阈值: $gap_cutoff"
read -p "确认执行? (Y/N): " confirm
[[ ! "$confirm" =~ ^[Yy]$ ]] && { echo "操作已取消"; exit 1; }

# 创建输出目录
mkdir -p "$output_directory"

# 处理文件
file_count=0
for ext in fna faa; do
    for file in "$input_directory"/*.$ext; do
        [[ -e "$file" ]] || continue
        
        if [[ "$ext" == "fna" ]]; then
            type="DNA"
        elif [[ "$ext" == "faa" ]]; then
            type="AA"
        fi
        
        filename=$(basename -- "$file")
        name_no_ext="${filename%.*}"
        output_file="$output_directory/${name_no_ext}.fas"
        
        ((file_count++))
        echo "处理第$file_count个文件: $filename"
        
        # 执行命令
        java -jar "$bmge_jar" -i "$file" -t "$type" -of "$output_file" -g "$gap_cutoff" -m "$matrix"
    done
done

# 结果报告
if (( file_count > 0 )); then
    echo -e "\n处理完成! 共处理 $file_count 个文件"
    echo "结果保存在: $output_directory"
else
    echo -e "\n警告: 未找到任何.fna或.faa文件!"
    echo "检查输入路径: $input_directory"
fi
