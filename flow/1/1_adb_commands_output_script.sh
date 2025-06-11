#!/bin/bash
# ADB自动化操作脚本
# 使用方法: chmod +x script.sh && ./script.sh

echo '开始执行ADB操作...'

echo '执行操作 1: adb shell input tap 936 1689'
adb shell input tap 936 1689
sleep 1  # 等待1秒

echo '所有ADB操作执行完成！'
