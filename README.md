# WPS Meeting Archive v1

本项目实现一个本机手动触发的 WPS 会议归档流程：

- Python CLI 调用 WPS 365 OpenAPI 拉取新会议、参会人、录制/纪要
- 如果标题本身是 `成员姓名1、成员姓名2_会议主题`，则自动解析主题
- 如果标题不是统一格式，则优先根据参会人 `user_id -> user_name` 自动填确认相关人员
- 如果标题不是统一格式，则进一步从录制内容的章节标题、摘要标题、转写关键词中自动提取 `确认主题`
- 调用 AirScript webhook 将候选会议写入 `待归档表`
- 调用 AirScript webhook 将老师已确认的待归档记录写入正式表 `文音视频档案`

## 目录

- `config.example.json`: 配置模板
- `wps_archive/`: Python CLI
- `airscript/upsert_pending_archive.js`: 待归档 upsert 脚本模板
- `airscript/finalize_pending_archive.js`: 正式归档脚本模板
- `airscript/bootstrap_pending_archive_schema.js`: 待归档表字段初始化脚本模板
- `tests/`: 本地单元测试

## 前置准备

### 1. 在 WPS 多维表中准备数据表

已有：

- `人员`
- `文音视频档案`

需要新增：

- `会议待归档表`

`会议待归档表` 字段名需与脚本模板保持一致：

- `会议ID`
- `会议标题`
- `会议日期`
- `会议链接`
- `确认相关人员`
- `确认主题`
- `确认类型`
- `确认标签`
- `归档状态`
- `备注`

`归档状态` 建议预置选项：

- `待确认`
- `确认归档`
- `已归档`
- `忽略`

`文音视频档案` 需要新增隐藏字段：

- `会议唯一ID`
- `来源会议标题`

### 2. 在 WPS AirScript 中创建两个脚本

- `upsert_pending_archive`
- `finalize_pending_archive`

把仓库中的两个脚本模板内容分别复制进去，保存后拿到各自 webhook。

### 3. 准备配置

复制模板：

```bash
cp config.example.json config.json
```

填入：

- WPS OpenAPI 访问凭证
- webhook
- 导师 user id
- 需要排除的人名
- 可选的 `topic_people_mapping` 人员-主题映射规则

`config.json` 是本机私有配置文件，包含 token、webhook 等敏感信息，不应提交到公开仓库。公开仓库只保留 `config.example.json` 作为模板。

## 标题格式

统一会议标题格式：

```text
成员姓名1、成员姓名2_会议主题
```

示例：

```text
栾天成_毕业设计
栾天成、褚梦圆_臭氧反演
麦泽霖_数据分析经验分享
```

默认规则：

- `_` 左边解析为成员姓名
- `_` 右边解析为主题
- `日期` 使用会议实际日期
- `类型` 默认写 `学术讨论`
- `标签` 默认写 `方案设计`
- `沈惠中` 这类排除名单中的姓名不会写入 `相关人员`
- 如果公开接口拿到的不是统一格式标题，则 `确认主题` 默认留空，等待老师确认
- `确认相关人员` 会优先根据参会人接口和 `/v7/users/{user_id}` 自动解析中文姓名

## 运行

### 解析标题测试

```bash
python3 -m wps_archive parse-title "栾天成、褚梦圆_臭氧反演"
```

### 同步候选会议到待归档表

```bash
python3 -m wps_archive --config /Users/evan/wps_robot/config.json sync-pending
```

这一步会自动：

- 拉取新会议
- 推断 `确认主题`
- 推断 `确认标签`
- 在 `确认相关人员` 为空时，结合参会人和 `topic_people_mapping` 自动回填人员

### 没有真实会议数据时，推送一条 mock 会议到待归档表

```bash
python3 -m wps_archive --config /Users/evan/wps_robot/config.json sync-mock "栾天成、褚梦圆_臭氧反演"
```

### 将已确认待归档记录写入正式表

```bash
python3 -m wps_archive --config /Users/evan/wps_robot/config.json finalize-confirmed
```

### 初始化待归档表字段

在 WPS AirScript 新建一个临时脚本，把 [`bootstrap_pending_archive_schema.js`](/Users/evan/wps_robot/airscript/bootstrap_pending_archive_schema.js) 的内容贴进去运行。

## 配置说明

CLI 默认优先使用 `auth.access_token`。

如果没有直接可用的 token，优先支持你当前已经验证过的 `client_credentials`：

- `auth.client_id`
- `auth.client_secret`

如果后续需要用户授权，也支持通过以下字段换取用户 token：

- `auth.client_id`
- `auth.client_secret`
- `auth.authorization_code`
- `auth.redirect_uri`

当前实现默认使用文档中的 OAuth token 接口：

- `https://openapi.wps.cn/oauth2/token`

当前本地默认已经按实测调整为：

- 会议列表：`GET /v7/meetings`
- 用户详情：`GET /v7/users/{user_id}`
- 请求字段：`start_time`、`end_time`、`page_size`
- 时间格式：Unix 秒级时间戳

当前第一版最稳的字段策略是：

- 自动填：`会议ID`、`会议日期`、`会议链接`、`会议标题`、`确认相关人员`、`确认类型`、`确认标签`、`归档状态`
- 老师确认：`确认主题`，必要时再修正 `确认相关人员`、`确认类型`、`确认标签`

### 人员-主题映射规则

`archive.topic_people_mapping` 支持按主题关键词推断学生，规则结构为：

```json
{
  "name": "何金玲",
  "priority": 20,
  "include_keywords": ["AI辅助55版本", "55版本", "化学机制开发"],
  "exclude_keywords": ["优化函数"]
}
```

规则说明：

- `priority` 越大优先级越高
- `include_keywords` 为命中词，至少命中一个才会进入排序
- `exclude_keywords` 为排除词，只要命中就跳过该规则
- 旧版 `keywords` 写法仍兼容，但推荐后续统一迁移到 `include_keywords`

示例：

```json
[
  {
    "name": "何金玲",
    "priority": 20,
    "include_keywords": ["AI辅助55版本", "55版本", "化学机制开发", "CMAQ化学机制"]
  },
  {
    "name": "麦泽霖",
    "priority": 10,
    "include_keywords": ["多物种反演", "伴随模型", "优化函数"],
    "exclude_keywords": ["AI辅助55版本", "55版本", "化学机制开发"]
  },
  {
    "name": "吴燕星",
    "priority": 10,
    "include_keywords": ["臭氧浓度机制", "臭氧机制", "NO2阈值", "季节机制"]
  }
]
```

如果你使用 `client_credentials` 仍然得到 `invalid connection`，通常说明会议数据还需要租户态或用户态 token，而不是单纯的应用级 token。

会议 API 路径和响应字段做成了可配置项，原因是你当前应用权限和实际返回结构可能与文档版本存在差异。若接口字段与默认值不一致，只需要改 `config.json`，不需要改 Python 代码。

## 测试

```bash
python3 -m unittest discover -s tests -v
```

## 参考文档

- WPS 365 OpenAPI 概述: https://open.wps.cn/documents/app-integration-dev/guide/start/overview.html
- 认证与授权概述: https://open.wps.cn/documents/app-integration-dev/wps365/server/certification-authorization/summary.html
- 获取用户 access_token: https://open.wps.cn/documents/app-integration-dev/wps365/server/certification-authorization/get-token/get-user-access-token.html
- AirScript APIToken 与 webhook: https://airsheet.wps.cn/docs/apitoken/intro.html
- AirScript API: https://airsheet.wps.cn/docs/apitoken/api.html
