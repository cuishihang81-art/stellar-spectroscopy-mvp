# 发布、分享与继续编辑

本项目推荐使用 **GitHub + Streamlit Community Cloud**：朋友只需打开一个网址，不必安装 Python；你仍然可以在本地或 GitHub 修改代码。推送到部署分支后，云端应用会自动更新。

## 公开分享（最省事）

### 1. 建立 GitHub 仓库

在 GitHub 新建一个空仓库，例如 `stellar-spectroscopy-mvp`。如果希望任何拿到链接的人都能直接体验，请选择 **Public**。

在本项目目录运行：

```bash
git init
git add .
git commit -m "Initial astronomy spectroscopy MVP"
git branch -M main
git remote add origin https://github.com/你的用户名/stellar-spectroscopy-mvp.git
git push -u origin main
```

`.venv/`、Python 缓存和 macOS 临时文件已被忽略，不会上传。运行应用需要的 `data/` 会上传；四个公开教程原始 FITS 也会保留，以便复现。

### 2. 部署到 Streamlit Community Cloud

1. 打开 <https://share.streamlit.io/> 并用 GitHub 登录。
2. 选择 **Create app** / **Deploy a public app from GitHub**。
3. 选择刚创建的仓库、`main` 分支和入口文件 `app.py`。
4. 在高级设置中选择 Python 3.12；本项目不需要 Secrets。
5. 点击 Deploy，完成后复制固定网址给朋友。

## 后续怎样编辑

本地编辑并测试：

```bash
source .venv/bin/activate
streamlit run app.py
```

确认后发布更新：

```bash
git add .
git commit -m "Describe this update"
git push
```

Streamlit Community Cloud 会从 GitHub 重新部署。也可以直接在 GitHub 网页中编辑文本文件并提交；较大的代码修改仍建议在本地完成。

## 如果不想公开源码或数据

可以把 GitHub 仓库设为 **Private**，再从 Streamlit Community Cloud 部署私有应用并管理受邀查看者。朋友需要登录，免费账户的私有应用与查看者数量可能有限。若只是不希望朋友修改代码，公开仓库已经足够：他们默认只有阅读和 fork 权限，不能直接写入你的仓库。

## 让同学一起改

- 少数固定合作者：在 GitHub 仓库的 Settings → Collaborators 中邀请对方。
- 课堂式协作：请同学 fork 仓库，通过 Pull Request 提交改进，更便于检查和回退。
- 不要把密码、令牌或私人数据提交进仓库；以后如需密钥，请使用 Streamlit 的 Secrets 设置。

## 发布前检查

```bash
python -m compileall app.py scripts/prepare_data.py
python -m streamlit run app.py
```

浏览器中依次完成六项任务，并确认图片、FITS 数据和演示 GIF 都能显示。
