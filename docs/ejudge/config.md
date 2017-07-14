# 配置

## 默认配置

- 初始密码：
    - 用户名：`ejudge`
    - 密码：`naive`

- 运行相关设置（更改以下设置需要重启服务器）
    - `TRACEBACK_LIMIT` 错误信息导出限制。
    - `COMPILE_MAX_TIME_FOR_TRUSTED` 判题程序最长编译时间（秒）。
    - `COMPILE_TIME_FACTOR` 提交程序的编译最多是时限的多少倍。
    - `REAL_TIME_FACTOR` 提交程序的总运行时长最多是时限的多少倍。
    - `MAX_WORKER_NUMBER` 最多运行多少个 worker，默认为核心数的 1/4。
    - `SECRET_KEY` 据说用于 socket 加密。
    - `USUAL_READ_SIZE` 编译错误信息读取多少字节

## 配置文件

配置文件在 `config/` 目录下。
