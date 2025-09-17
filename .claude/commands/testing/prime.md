---
allowed-tools: Bash, Read, Write, LS
---

# 准备测试环境

此命令通过检测测试框架、验证依赖项和配置测试运行器代理来准备测试环境，以实现最佳的测试执行。

## 飞行前检查清单

在继续之前，完成这些验证步骤。
不要用飞行前检查进度（"我不会..."）打扰用户。只需完成它们并继续前进。

### 1. 测试框架检测

**JavaScript/Node.js：**
- 检查package.json中的测试脚本：`grep -E '"test"|"spec"|"jest"|"mocha"' package.json 2>/dev/null`
- 查找测试配置文件：`ls -la jest.config.* mocha.opts .mocharc.* 2>/dev/null`
- 检查测试目录：`find . -type d \( -name "test" -o -name "tests" -o -name "__tests__" -o -name "spec" \) -maxdepth 3 2>/dev/null`

**Python：**
- 检查pytest：`find . -name "pytest.ini" -o -name "conftest.py" -o -name "setup.cfg" 2>/dev/null | head -5`
- 检查unittest：`find . -path "*/test*.py" -o -path "*/test_*.py" 2>/dev/null | head -5`
- 检查requirements：`grep -E "pytest|unittest|nose" requirements.txt 2>/dev/null`

**Rust：**
- 检查Cargo测试：`grep -E '\[dev-dependencies\]' Cargo.toml 2>/dev/null`
- 查找测试模块：`find . -name "*.rs" -exec grep -l "#\[cfg(test)\]" {} \; 2>/dev/null | head -5`

**Go：**
- 检查测试文件：`find . -name "*_test.go" 2>/dev/null | head -5`
- 检查go.mod是否存在：`test -f go.mod && echo "找到Go模块"`

**其他语言：**
- Ruby：检查RSpec：`find . -name ".rspec" -o -name "spec_helper.rb" 2>/dev/null`
- Java：检查JUnit：`find . -name "pom.xml" -exec grep -l "junit" {} \; 2>/dev/null`

### 2. 测试环境验证

如果未检测到测试框架：
- 告诉用户："⚠️ 未检测到测试框架。请指定您的测试设置。"
- 询问："我应该使用什么测试命令？（例如：npm test, pytest, cargo test）"
- 存储响应以供将来使用

### 3. 依赖项检查

**对于检测到的框架：**
- Node.js：运行`npm list --depth=0 2>/dev/null | grep -E "jest|mocha|chai|jasmine"`
- Python：运行`pip list 2>/dev/null | grep -E "pytest|unittest|nose"`
- 验证测试依赖项已安装

如果缺少依赖项：
- 告诉用户："❌ 测试依赖项未安装"
- 建议："运行：npm install（或 pip install -r requirements.txt）"

## 指令

### 1. 框架特定配置

基于检测到的框架，创建测试配置：

#### JavaScript/Node.js (Jest)
```yaml
framework: jest
test_command: npm test
test_directory: __tests__
config_file: jest.config.js
options:
  - --verbose
  - --no-coverage
  - --runInBand
environment:
  NODE_ENV: test
```

#### JavaScript/Node.js (Mocha)
```yaml
framework: mocha
test_command: npm test
test_directory: test
config_file: .mocharc.js
options:
  - --reporter spec
  - --recursive
  - --bail
environment:
  NODE_ENV: test
```

#### Python (Pytest)
```yaml
framework: pytest
test_command: pytest
test_directory: tests
config_file: pytest.ini
options:
  - -v
  - --tb=short
  - --strict-markers
environment:
  PYTHONPATH: .
```

#### Rust
```yaml
framework: cargo
test_command: cargo test
test_directory: tests
config_file: Cargo.toml
options:
  - --verbose
  - --nocapture
environment: {}
```

#### Go
```yaml
framework: go
test_command: go test
test_directory: .
config_file: go.mod
options:
  - -v
  - ./...
environment: {}
```

### 2. 测试发现

扫描测试文件：
- 计算找到的测试文件总数
- 识别使用的测试命名模式
- 记录任何测试工具或辅助程序
- 检查测试装置或数据

```bash
# Node.js示例
find . -path "*/node_modules" -prune -o -name "*.test.js" -o -name "*.spec.js" | wc -l
```

### 3. 创建测试运行器配置

使用发现的信息创建`.claude/testing-config.md`：

```markdown
---
framework: {detected_framework}
test_command: {detected_command}
created: [使用来自date -u +"%Y-%m-%dT%H:%M:%SZ"的真实日期时间]
---

# 测试配置

## 框架
- 类型：{framework_name}
- 版本：{framework_version}
- 配置文件：{config_file_path}

## 测试结构
- 测试目录：{test_dir}
- 测试文件：找到{count}个文件
- 命名模式：{pattern}

## 命令
- 运行所有测试：`{full_test_command}`
- 运行特定测试：`{specific_test_command}`
- 调试运行：`{debug_command}`

## 环境
- 必需的ENV变量：{list}
- 测试数据库：{如果适用}
- 测试服务器：{如果适用}

## 测试运行器代理配置
- 使用详细输出进行调试
- 顺序运行测试（无并行）
- 捕获完整堆栈跟踪
- 无模拟 - 使用真实实现
- 等待每个测试完成
```

### 4. 配置测试运行器代理

基于框架准备代理上下文：

```markdown
# 测试运行器代理配置

## 项目测试设置
- 框架：{framework}
- 测试位置：{directories}
- 测试总数：{count}
- 上次运行：从未

## 执行规则
1. 始终使用`.claude/agents/test-runner.md`中的测试运行器代理
2. 以最大详细程度运行进行调试
3. 无模拟服务 - 使用真实实现
4. 顺序执行测试 - 无并行执行
5. 捕获包括堆栈跟踪的完整输出
6. 如果测试失败，在假设代码问题之前分析测试结构
7. 报告带有上下文的详细失败分析

## 测试命令模板
- 完整套件：`{full_command}`
- 单个文件：`{single_file_command}`
- 模式匹配：`{pattern_command}`
- 监视模式：`{watch_command}`（如果可用）

## 要检查的常见问题
- 环境变量正确设置
- 测试数据库/服务正在运行
- 依赖项已安装
- 正确的文件权限
- 运行之间清洁的测试状态
```

### 5. 验证步骤

配置后：
- 尝试运行简单测试以验证设置
- 检查测试命令是否有效：`{test_command} --version`或等效命令
- 验证测试文件可被发现
- 确保没有权限问题

### 6. 输出摘要

```
🧪 测试环境已准备

🔍 检测结果：
  ✅ 框架：{framework_name} {version}
  ✅ 测试文件：{count}个文件在{directories}中
  ✅ 配置：{config_file}
  ✅ 依赖项：全部已安装

📋 测试结构：
  - 模式：{test_file_pattern}
  - 目录：{test_directories}
  - 工具：{test_helpers}

🤖 代理配置：
  ✅ 测试运行器代理已配置
  ✅ 详细输出已启用
  ✅ 顺序执行已设置
  ✅ 真实服务（无模拟）

⚡ 就绪命令：
  - 运行所有测试：/testing:run
  - 运行特定测试：/testing:run {test_file}
  - 运行模式：/testing:run {pattern}

💡 提示：
  - 始终以详细输出运行测试
  - 如果测试失败，检查测试结构
  - 使用真实服务，不是模拟
  - 让每个测试完全完成
```

### 7. 错误处理

**常见问题：**

**未检测到框架：**
- 消息："⚠️ 未找到测试框架"
- 解决方案："请手动指定测试命令"
- 存储用户响应以供将来使用

**缺少依赖项：**
- 消息："❌ 测试框架未安装"
- 解决方案："先安装依赖项：npm install / pip install -r requirements.txt"

**无测试文件：**
- 消息："⚠️ 未找到测试文件"
- 解决方案："先创建测试或检查测试目录位置"

**权限问题：**
- 消息："❌ 无法访问测试文件"
- 解决方案："检查文件权限"

### 8. 保存配置

如果成功，为将来的会话保存配置：
- 存储在`.claude/testing-config.md`中
- 包括所有发现的设置
- 如果检测到更改，在后续运行时更新

## 重要说明

- **始终检测**而不是假设测试框架
- **在声明就绪之前验证依赖项**
- **为调试配置** - 详细输出至关重要
- **无模拟** - 使用真实服务进行准确测试
- **顺序执行** - 避免并行测试问题
- **存储配置**以保持未来运行的一致性

$ARGUMENTS
