# API

## 快速检索

+ `GET /ping` 如果成功，返回 pong
+ `POST /upload/case/:fid/:io` 上传测试用例，永久保存
+ `POST /upload/:type` 上传测试程序，永久保存
+ `DELETE /delete/case/:fid` 删除指定的测试用例（不建议）
+ `DELETE /delete/:type/:fid` 删除测试程序（不建议）
+ `POST /generate` 生成输入
+ `POST /validate` 验证输入
+ `POST /stress` 压力测试（用于测试某一可能错误的程序的正确性）
+ `POST /judge/result` 提交一组判题（往往用于测试）
+ `POST /judge/output` 根据输入和程序，生成输出
+ `POST /judge/sandbox` 返回程序运行的原始沙盒结果
+ `POST /judge/checker` 返回程序输出检查器的运行结果
+ `POST /judge/interactor` 返回交互程序的运行结果
+ `POST /judge` 提交判题

另有：socket.io `judge` 事件用于提交判题，格式与 `POST /judge` 相同。

注：不建议删除的原因是：容易造成业务逻辑混乱。而且大多数提交程序占用空间并不大，定期清理即可。

## RESTful API

- 除上传测试用例需要直接将文件放在 POST 的数据中之外，其余 API 全部采用 JSON。Response 也全部使用 JSON。
- auth 请使用指定的用户名密码。可在 `/reset` 页面查询和设置。初始密码为空。

示例：

```python
import requests
token = ('ejudge', 'password')  # token is a tuple
data = {'fingerprint': '123123'}  # data is a dict
response = requests.post(url, json=data, auth=token).json()  # response is a dict
```

回复 JSON 中，一般有：

+ `status`: `received` 或 `reject`。
+ `message` (可能没有)
    + 如果是 `reject`，通常是拒绝的原因，如果出错，通常有 traceback。
    + 如果是 `received`，可能有结果信息。

`status` 和 `message` 有特殊含义的，会在 API 中注明。会返回其他键值对的，也会在 API 中注明。否则就按照上述标准。

在文档中，字段名的含义是统一的。一旦解释过一次，下面的解释将从简处理。

### `POST /upload/case/:fid/:io`

+ `:fid` 测试用例指纹。
+ `:io` 是输入还是输出。取值：
    + `input` 表示这是输入文件
    + `output` 表示这是输出文件
+ 上传测试用例的二进制形式。

示例：

```python
url = 'http://example.com/upload/case/ff123123/input'
result = requests.post(url, data=open(input_file, 'rb').read(), auth=token).json()
```

### `POST /upload/:type`

+ `:type` 可以是 `checker`, `validator`, `generator`, `interactor`。
+ `fingerprint` 指纹
+ `lang` 语言，必须是在 `lang.yaml` 中支持的语言
+ `code` 代码（文本）

示例：

```json
{
  "fingerprint": "23332333",
  "lang": "cc11",
  "code": "#include <iostream> ...."
}
```

### `POST /generate`

+ `fingerprint`
+ `lang`
+ `code`
+ `max_time` 最长运行时间（浮点数，单位是秒）
+ `max_memory` 最大运行内存（浮点数，单位是 MB）
+ `command_line_args` 本次生成所使用的命令行参数（必须是由字符串组成的列表，可以为空）

**注意：如果提交的程序已经 upload 过，那么该程序可能不会重复编译。**

示例：

```json
{
  "fingerprint": "23332333",
  "lang": "cc11",
  "code": "#include <iostream> ....",
  "max_time": 1.0,
  "max_memory": 256,
  "command_line_args": ["1", "5", "90"]
}
```

响应（成功）：

```json
{
  "status": "received",
  "output": "MTAgMTAgMjAKMyA4CjYgNgo1IDIKNSA2CjQgOQoyIDQKMTAgMwoyIDgKMyA5CjkgMwo4IDYKOCAxMAo1IDgKNyA0CjQgNAozIDYKMTAgMgo3IDcKMyAxCjIgMwo="
}
```

注意字段名称是 `output`。
**响应的生成器输出是 base64 编码的**。使用 `base64.b64decode(encoded).decode()` 来解码。

### `POST /validate`

+ `fingerprint`
+ `lang`
+ `code`
+ `max_time`
+ `max_memory`
+ `input` 输入数据，base64，可以使用 `base64.b64encode(binary_data).decode()` 来编码。

```json
{
  "fingerprint": "23332333",
  "lang": "cc11",
  "code": "#include <iostream> ....",
  "max_time": 1.0,
  "max_memory": 256,
  "input": "MTAgMTAgMjAKMyA4CjYgNgo1IDIKNSA2CjQgOQoyIDQKMTAgMwoyIDgKMyA5CjkgMwo4IDYKOCAxMAo1IDgKNyA0CjQgNAozIDYKMTAgMgo3IDcKMyAxCjIgMwo="
}
```

响应（成功）：

```json
{
  "verdict": -1,
  "status": "received",
  "message": ""
}
```

（这里的 -1 表示不通过）

### `POST /stress`

+ `std` 对象，含 `fingerprint`, `lang`, `code` 三个字段，表示标程。
+ `submission` 对象，表示可能是错误的程序。
+ `generator` 对象，表示数据生成器。
+ `command_line_args_list` **嵌套列表**，表示数据生成器要循环执行使用的一系列参数。这些参数将从第一个开始逐一使用，用完回到第一个循环使用。
+ `max_time`
+ `max_memory`
+ `max_sum_time` 压力测试总时间，单位是秒
+ `checker` 对象，输出验证程序
+ `interactor` 可选。对象，交互程序
+ `max_generate` 可选。最多获得多少组错误数据（默认为 5）

示例：

```json
{
  "std": {
    "lang": "cpp",
    "fingerprint": "test_KKMoKBcaSjpEjCxdNpKyaJHrdWmTZfFd",
    "code": "#include <cmath>\n#includ..."
  },
    "submission": {
    "lang": "python",
    "fingerprint": "test_JBUfXirWpDgsNBXMhYDgjmBOwARvHLYZ",
    "code": "a, b = map(int, input().split())\nif a % 2 == 0:\n    print(a + b + 1)\nelse:\n    print(a + b)"
  },
  "generator": {
    "lang": "python",
    "fingerprint": "test_tKRaqNvnRbZwoUsNVITjrwZgENyShwLq",
    "code": "import random\nprint(random.randint(1, 100), random.randint(1, 100))"
  },
  "max_time": 1,
  "max_sum_time": 20,
  "max_memory": 128,
  "checker": {
    "lang": "cpp",
    "fingerprint": "test_DAcejcYaQGcspoEhEkSYjwtQssiKoZsn",
    "code": "#include ..."
  },
  "command_line_args_list": [
    []
  ]
}
```

响应：

```json
{
  "output": ["MTIgNAo=", "NTYgNjYK", "ODYgMzUK", "NTIgOTgK", "NCAzMAo="],
  "status": "received"
}
```

`output` 为出现错误的数据，最多 `max_generate` 组。

### `POST /judge/output`, `POST /judge/sandbox`

+ `submission` 对象，表示提交程序。
+ `max_time`
+ `max_memory`
+ `input` 输入数据，base64。
+ `interactor` 可选，如果是交互程序，需指定。

示例：

```json
{
  "input": "MSAy",
  "max_time": 1,
  "max_memory": 128,
  "submission": {
    "lang": "cpp",
    "fingerprint": "test_RHEstOxREhabNQSInDaNqZbJlJoDGruz",
    "code": "#include <cmath>\n#include <cstdio..."
  }
}
```

响应：

```json
{
  "output": "Mwo=",
  "status": "received"
}
```

sandbox 请求响应：

```json
{
  "time": 0.0,
  "exit_code": 0,
  "verdict": 0,
  "status": "received",
  "memory": 40.71875,
  "signal": 0
}
```

### `POST /judge/checker`, `POST /judge/interactor`

+ `submission`
+ `max_time`
+ `max_memory`
+ `input`
+ `output` 与 `input` 同理。
+ `checker` 对象，指定输出检查。
+ `interactor` 可选。

示例：

```json
{
  "input": "MSAy",
  "output": "Mw==",
  "max_time": 1,
  "max_memory": 128,
  "submission": {
    "lang": "cpp",
    "fingerprint": "test_RHEstOxREhabNQSInDaNqZbJlJoDGruz",
    "code": "#include <cmath>\n#include <cstdio..."
  },
  "checker": {
    "lang": "cpp",
    "fingerprint": "test_DAcejcYaQGcspoEhEkSYjwtQssiKoZsn",
    "code": "#include ..."
  }
}
```

响应：

```json
{
  "time": 0.0,
  "status": "received",
  "verdict": 0,
  "message": "1 number(s): \"3\""
}
```

对于 `interactor`，`checker`, `output` 不是必选参数。返回结果与 `checker` 类似：

```json
{
  "verdict": 0,
  "status": "received",
  "message": "1 queries processed"
}
```

### `POST /judge/result`

+ `submission`
+ `max_time`
+ `max_memory`
+ `input`
+ `output`
+ `checker`
+ `interactor`

请求示例略。

返回结果规则如下：

+ 如果 `verdict` 是 `ACCEPTED` (0)，有一个字段名为 `time`，记录程序运行时间。
+ 如果 `verdict` 是 `RUNTIME_ERROR` (4)，有一个字段名为 `message`，记录出现错误的信号 (signal) 类型。
+ 如果 `verdict` 是 `COMPILE_ERROR` (6)，`message` 字段中记录的是编译错误信息。
+ 否则，`message` 中一定是 traceback，此时可能没有 `verdict`。

### multiple 选项

在下列 API 中：

+ `POST /generate`
+ `POST /validate`
+ `POST /judge/result`
+ `POST /judge/output`
+ `POST /judge/sandbox`
+ `POST /judge/checker`
+ `POST /judge/interactor`

可以增加 multiple 字段。例如：

```json
{
  "input": ["MSAy", "..."],
  "max_time": 1,
  "max_memory": 128,
  "multiple": true,
  "submission": {
    "lang": "cpp",
    "fingerprint": "test_RHEstOxREhabNQSInDaNqZbJlJoDGruz",
    "code": "#include <cmath>\n#include <cstdio..."
  }
}
```

如你所见，如果 multiple 为真，对应的 input, output 需要是一个列表。在 generate 中，命令行参数需要是一个列表的列表，如果有输出，输出也要是一个列表。
输出列表中的值应与输入列表一一对应。返回结果，除了 status 外，也会被包裹在列表内。具体为：

+ 对于 `/generate`, output 会变成一个列表；
+ 对于其他 API，多一个名为 result 的字段，为一个列表，列表内含有多个字典，按次序返回结果。

例如：

```json
{
  "output": [
    "MTAgMTAgMjAKMyA4CjYgNgo1IDIKNSA2CjQgOQoyIDQKMTAgMwoyIDgKMyA5CjkgMwo4IDYKOCAxMAo1IDgKNyA0CjQgNAozI...",
    "NDAwIDQwMCA4MDAwCjM5OSAyODkKMjg2IDM2MwoxODAgMTc1CjI1NSAxOTMKMzQ3IDM1NwozMTkgMzYKMzQ2IDg2CjI3NiAxM...",
    "NDAgNDAgMTUwMAoxNyAyOQo0IDMwCjM2IDE5CjE4IDE1CjM4IDEKMjkgMzIKMjMgMzcKMjcgNDAKMiAxNwozMCAyMAoxOCAzM..."
  ],
  "status": "received"
}
```

```json
{
  "result": [
    {
      "time": 0.0,
      "message": "1 number(s): \"3\"",
      "verdict": 0
    },
    {
      "time": 0.0,
      "message": "1 number(s): \"7\"",
      "verdict": 0
    }
  ],
  "status": "received"
}
```


### `POST /judge`

+ `code`
+ `fingerprint`
+ `max_time`
+ `max_memory`
+ `lang`
+ `run_until_complete` 布尔值，默认为 False，若为 True，即使中间的测试数据出错也会一直跑下去，用于 OI 赛制等。
+ `cases` 有序列表，测试用例指纹。返回结果也按照这个顺序
+ `checker` 输出检查程序指纹
+ `interactor` 交互题中的交互程序指纹

（最后几项必须预先上传）

```json
{
  "code": "...",
  "fingerprint": "test_HsgxUjDlvjzLxuaWWcNMlVzAauCWsmGE",
  "max_time": 1,
  "max_memory": 128,
  "lang": "cpp",
  "cases": [
    "test_rZiIjfMTkNFGKiIMZtsQaOHMrUKOyMNa",
    "test_gsjwbFPcZsezMCAFiGsbUbFecHAnVcjH",
    "test_hviQVygNCitYmGTNJkvfOCZFRvPdTLBx"
  ],
  "checker": "test_anJkjSdGIxBzaMSJwqXSbIWeIeBkxJLi"
}
```

响应：
```json
{
  "detail": [
    {"verdict": 0, "time": 0.0},
    {"verdict": 0, "time": 0.0},
    {"verdict": 0, "time": 0.0}
  ],
  "verdict": 0,
  "status": "received"
}
```

包括一个每次的判定结果（结果格式见 `POST /judge/result`），一个总判决。总判决由第一个出错（不是 0）的判决决定。

若不幸 Compile Error，总 `message` 中会有编译错误信息：

```json
{
  "verdict": 6,
  "message": "/tmp/pycharm_project_...tOQjlGDTCQnEKQ",
  "detail": [],
  "status": "received"
}
```

但对于 Runtime Error 的情况，错误信息是在 `detail` 中的每一次运行内的。


## Socket.io

对于 socket.io，提供了 `judge` 事件，也就是上面的 `/judge` API。传入 JSON 几乎相同，但需要手动添加验证信息：

```python
data.update(username=token[0], password=token[1])
```

你可能需要监听 `judge_reply` 事件，因为回复都是这里来的。

由于 Python 对于 socket.io 客户端的支持不佳，所以可能要用到不大好用的 socketio-client。然后可以直接 emit 字典哦。

```python
from socketIO_client import SocketIO, LoggingNamespace
result = None

def callback(*args):
    nonlocal news_length, result
    body = args[0]
    if body.get('verdict') != Verdict.JUDGING.value:
        result = body
    # emit to user

with SocketIO('localhost', 5000, LoggingNamespace) as socketIO:
    socketIO.emit('judge', data)
    socketIO.on('judge_reply', callback)
    while not result:
        socketIO.wait(seconds=1)
```

推荐的使用方案是，先使用 socket.io 进行判题，若失败，则回滚到 requests 请求。

