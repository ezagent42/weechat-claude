# 发布流程

## 版本号规则

版本号由 `hatch-vcs` 从 git tag 自动派生：

| 场景 | 版本号 | 示例 |
|------|--------|------|
| 打 tag 的 commit | `X.Y.Z` | `0.3.0` |
| tag 之后的 N 个 commit | `X.Y.(Z+1).devN` | `0.3.1.dev17` |
| 下一个 release | 打新 tag `vX.Y.Z` | `v0.4.0` |

**原则：除非明确说明要 release，只推 dev 版本。不手动改版本号。**

## PR 合并后更新 PyPI + Homebrew

每次 PR 合并到 main 后，执行以下步骤发布新的 dev 版本：

### 1. 打 tag 触发 PyPI 发布

```bash
cd /path/to/zchat
git pull origin main

# 查看当前版本号（hatch-vcs 自动计算）
uv build 2>&1 | grep "Successfully built"
# → Successfully built dist/zchat-0.3.1.dev18.tar.gz

# 用 build 输出的版本号打 tag
git tag v0.3.1.dev18
git push origin v0.3.1.dev18
```

CI（`.github/workflows/publish.yml`）会自动 build + publish 到 PyPI。

等 CI 完成（约 1 分钟）：
```bash
gh run list -L 1  # 确认 ✅
```

### 2. 更新 Homebrew formula

从 PyPI 获取新版本的 URL 和 sha256，更新 `homebrew-zchat/Formula/zchat.rb`：

```bash
# 获取 PyPI sdist URL 和 hash（替换版本号）
VERSION=0.3.1.dev18
curl -s "https://pypi.org/pypi/zchat/$VERSION/json" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); \
    [print(f'url: {u[\"url\"]}\nsha256: {u[\"digests\"][\"sha256\"]}') \
    for u in d['urls'] if u['url'].endswith('.tar.gz')]"

# 编辑 formula — 替换 url 和 sha256
cd homebrew-zchat
# 修改 Formula/zchat.rb 中的 url 和 sha256 行

git add Formula/zchat.rb
git commit -m "bump zchat to $VERSION"
git push
```

### 3. 用户更新

```bash
brew update && brew upgrade zchat
zchat --version  # 确认新版本
```

## 正式 Release（需要明确说明时）

```bash
# 1. 确保 main 干净
git checkout main && git pull

# 2. 打 release tag（这会让 hatch-vcs 生成干净的版本号）
git tag v0.4.0
git push origin v0.4.0

# 3. CI 自动发布到 PyPI (版本号: 0.4.0)
# 4. 更新 Homebrew formula（同上步骤 2）
```

## 子模块发布

`zchat-protocol` 和 `zchat-channel-server` 有独立的 PyPI 包和版本号。
只在它们的代码有改动时才需要发布新版：

```bash
cd zchat-channel-server  # 或 zchat-protocol
# 修改 pyproject.toml 中的 version
git add pyproject.toml && git commit -m "bump version to X.Y.Z"
git tag vX.Y.Z && git push && git push origin vX.Y.Z
# CI 自动发布
```

然后更新 zchat 主包的 `pyproject.toml` 中对应的 `>=X.Y.Z` 依赖版本。

## 注意事项

- **不要手动改 `zchat/_version.py`** — 它由 hatch-vcs 在 build 时自动生成
- **不要用 `v0.3.0.devN` 格式的 tag** — hatch-vcs 不支持，会报错
- **tag 格式必须是 `vX.Y.Z` 或 `vX.Y.Z.devN`**（后者由 hatch-vcs 计算，tag 名用 build 输出的版本号）
- `pyproject.toml` 中 `local_scheme = "no-local-version"` 确保版本号不含 `+gHASH`（PyPI 不接受 local segment）
- Homebrew formula 的 `force-include` 不要重复包含 `packages` 已覆盖的目录（会导致 PyPI 400）
