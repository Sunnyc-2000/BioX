#!/bin/bash
# Modified by DeepSeek R1 for interactive operation and improved file handling (20250528)

# 交互式参数输入
echo "请输入数据目录路径："
read -r data_dir
echo "请输入样本列表（以空格分隔）："
read -r sample_list
echo "请输入配置目录路径："
echo "（配置目录的文件需包括名字为“config.txt”以及“seed.fasta”的两个文件）"
read -r config_dir

# 转换为数组
samples=($sample_list)

# 验证输入目录
validate_directory() {
    if [ ! -d "$1" ]; then
        echo "错误：目录不存在 - $1"
        exit 1
    fi
}

validate_directory "$data_dir"
validate_directory "$config_dir"

# 主处理循环
for sample in "${samples[@]}"; do
    echo "开始处理样本: $sample"
    sample_dir="$data_dir/$sample"
    result_dir="$sample_dir/novo${sample}mito"
    
    # 1. 检查样本目录是否存在
    if [ ! -d "$sample_dir" ]; then
        echo "警告：样本目录不存在 - $sample_dir，跳过"
        continue
    fi
    
    # 2. 清理旧文件和目录
    echo "清理旧文件和目录..."
    cd "$sample_dir" || {
        echo "错误：无法进入目录 $sample_dir"
        exit 1
    }
    
    # 定义需要清理的文件模式（增加新文件类型）
    cleanup_files=(
        "config.txt"
        "${sample}config.txt"
        "seed.fasta"
        "novo${sample}log.txt"
        "Circularized_assembly_1_${sample}.*"
        "contigs_tmp_${sample}.*"
        "log_${sample}.*"
        "NOVOPlasty.log"
        "seed_used.txt"
        "Option_1_${sample}.fasta"           # 新增清理项
        "Merged_contigs_${sample}.txt"        # 新增清理项
        "Contigs_1_${sample}.fasta"           # 新增清理项
    )
    
    # 删除可能残留的文件
    for pattern in "${cleanup_files[@]}"; do
        find . -maxdepth 1 -name "$pattern" -delete
    done
    
    # 3. 删除可能残留的结果目录
    if [ -d "$result_dir" ]; then
        rm -rf "$result_dir"
        echo "已删除旧结果目录: $result_dir"
    fi
    
    # 4. 复制配置文件和seed
    echo "复制配置文件及种子文件..."
    for file in "config.txt" "seed.fasta"; do
        cp -v "$config_dir/$file" "$sample_dir/" || {
            echo "错误：无法复制 $file 文件"
            exit 1
        }
    done
    
    # 5. 重命名配置文件
    new_config="${sample}config.txt"
    mv -v "config.txt" "$new_config"
    
    # 6. 修改配置文件参数
    echo "更新配置文件内容..."
    sed -i "/^Project name/c\Project name          = $sample" "$new_config"
    sed -i "/^Forward reads/c\Forward reads         = ${sample}_1.clean.fq.gz" "$new_config"
    sed -i "/^Reverse reads/c\Reverse reads         = ${sample}_2.clean.fq.gz" "$new_config"
    
    # 7. 运行Novoplasty并记录日志
    log_file="novo${sample}log.txt"
    echo "运行分析程序..."
    start_time=$(date +%s)
    
    # 检查Novoplasty脚本
    novo_script="/home/insect303/novoplasty/NOVOPlasty-NOVOPlasty4.3.5/NOVOPlasty4.3.5.pl"
    if [ ! -f "$novo_script" ]; then
        echo "错误：未找到Novoplasty脚本 - $novo_script"
        exit 1
    fi
    
    # 运行命令
    perl "$novo_script" -c "$new_config" &> "$log_file"
    exit_code=$?
    
    # 8. 创建结果目录
    echo "创建结果目录: $result_dir"
    mkdir -p "$result_dir"
    
    # 9. 定义所有可能的结果文件模式（包含新增文件）
    result_files=(
        "Circularized_assembly_1_$sample.fasta"
        "contigs_tmp_$sample.txt"
        "log_$sample.txt"
        "Option_1_${sample}.fasta"          # 新增结果文件
        "Merged_contigs_${sample}.txt"      # 新增结果文件
        "Contigs_1_${sample}.fasta"         # 新增结果文件
        "$log_file"
        "$new_config"
        "seed.fasta"
        "Circularized_assembly_1_*.fasta"
        "contigs_tmp_*.txt"
        "log_*.txt"
        "NOVOPlasty.log"
        "seed_used.txt"
        "*.png"                             # 可能生成的图表
    )
    
    # 10. 移动所有结果文件（包含可能的新文件）
    moved_count=0
    for pattern in "${result_files[@]}"; do
        find . -maxdepth 1 -name "$pattern" -exec mv -t "$result_dir" {} + 
        count=$(find . -maxdepth 1 -name "$pattern" | wc -l)
        moved_count=$((moved_count + count))
    done
    
    # 11. 处理运行结果
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    if [ $exit_code -eq 0 ]; then
        # 检查关键文件是否存在
        key_files=(
            "Circularized_assembly_1_${sample}.fasta"
        )
        
        missing_files=()
        for file in "${key_files[@]}"; do
            [ -f "$result_dir/$file" ] || missing_files+=("$file")
        done
        
        if [ ${#missing_files[@]} -gt 0 ]; then
            echo "警告：缺少${#missing_files[@]}个关键文件"
            printf '  - %s\n' "${missing_files[@]}"
        else
            echo "成功：分析完成并生成关键文件"
        fi
    else
        echo "错误：分析运行失败（退出代码: $exit_code）"
    fi
    
    # 12. 输出统计信息
    echo "样本 $sample 处理完成 | 耗时: $duration 秒"
    echo "移动文件: $moved_count 个"
    echo "输出目录内容:"
    ls -lh "$result_dir" | awk 'NR>1 {print $9, $5}'
    echo "------------------------------------------"
done

echo "所有样本处理完成！"
exit 0
