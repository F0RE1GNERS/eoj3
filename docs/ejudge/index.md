# eJudge

## 文档局限性

这里的文档面向正在开发中的 ejudge v2。v1（目前 master 分支）的文档不再更新。

## 简介

eJudge 是 eoj3 捆绑销售的判题服务器。主要职责是提供判题服务（废话）。设计判题服务器的主要意图有二：

- 负载均衡：可以根据比赛需求添加减少判题服务器，在节省资源的同时，保证判题速度。
- 运行安全：提交的代码是不受信任的。在单独的判题服务器中运行方便意外情况的处理。

此外，相比其他 OJ 判题服务器，eJudge 还具有以下特色：

- 使用 Docker 急速部署，方便重启。
- 判题服务提供了 socket.io 和 RESTful API 两种方式，方便判题进程的即时响应及更新。
- 支持 generator, validator, stress test 等测试工具的运行，为 Polygon system 提供支持（开发中）。
- 由于在出题过程中程序运行不受限制，「非常危险」，建议采用出题用服务器与主判题服务器相隔离的办法。运行两个服务器，互不干涉。也不用担心泄露数据。

## 判题服务器设计

为方便读者理解，这里对每个类的设计初衷进行解释。

### 测试用例 (Case)

每一个测试用例都有一个**指纹** (fingerprint)，这一指纹在上传测试用例的时候就已经指定。请确保指纹的安全性，指纹不应该是由用户指定的，应避免出现 `../../finger` 这样的情况。
同时需要注意的是，指定指纹的时候应尽可能避免使用 32 位纯字母指纹，避免冲突（虽然冲突概率非常低）。

测试用例含 input 和 output，分别为输入和输出。如果只有 input，那就不能称为测试用例，即使上传 input 也只会带来异常。
要根据 input 生成 output 需要调用另外的 API。

### 程序 (Submission)

所有在判题服务器上运行的程序的基类。Submission 本身提供了运行（run）方法，默认开启沙盒运行。

所有程序都有一个**指纹** (fingerprint)，如何获得指纹判题服务器不关心，但应确保唯一。受信任程序是可以永久保存的，
对于受信任程序而言，指纹尤其重要，因为每一个判题请求都需要指定对应的输出检查器，这种指定就是通过指纹来实现的。

### 受信任程序 (SpecialProgram)

下称**测试程序**。测试程序并不是一定用于判题的，也可能用于生成数据等等。此类程序的共同特点是可能有文件操作，所以沙盒限制较为宽松。
由用户提交的受信任程序需在 Polygon 中运行，用户需同意不破坏原则。

#### 输出检查 (Checker)

提供对输出进行检查的程序。

#### 输入检查 (Validator)

提供对输入进行检查的程序。

#### 生成器 (Generator)

用于生成输入数据。

#### 交互 (Interactor)

用于交互题。

详细用法参见 EOJ Polygon 的介绍。

### 运行 (CaseRunner)

一个组合了测试用例、提交程序、测试程序的类，提供方便的运行功能，并且可以指定输出的结果（返回什么）。

### 判定结果 (Verdict)

+ WAITING = -3
+ JUDGING = -2
+ WRONG_ANSWER = -1
+ ACCEPTED = 0
+ TIME_LIMIT_EXCEEDED = 1
+ IDLENESS_LIMIT_EXCEEDED = 2
+ MEMORY_LIMIT_EXCEEDED = 3
+ RUNTIME_ERROR = 4
+ SYSTEM_ERROR = 5
+ COMPILE_ERROR = 6
+ JUDGE_ERROR = 11

## 支持的语言

括号内是在 `lang` 字段中填写的。

+ C (c)
+ C++ 11 (cpp)
+ C++ 14 (cc14)
+ C# (cs)
+ Pascal (pas)
+ Java (java)
+ Python 2 (py2)
+ Python 3 (python)
+ Pypy (pypy)
+ Perl (perl)
+ OCaml (ocaml)
+ PHP (php)
+ Rust (rs)
+ Haskell (hs)
+ Javascript (js)

（部分语言命名诡异是为了确保向下兼容性。）

## 安装

### 部署

Docker：`curl -sSL http://acs-public-mirror.oss-cn-hangzhou.aliyuncs.com/docker-engine/internet | sh -`

外网：`sudo docker pull registry.cn-hangzhou.aliyuncs.com/ultmaster/ejudge:v2`

阿里云内网：`sudo docker pull registry-internal.cn-hangzhou.aliyuncs.com/ultmaster/ejudge:v2`

运行：`sudo docker run -d -p YOUR_RORT:5000 registry-internal.cn-hangzhou.aliyuncs.com/ultmaster/ejudge:v2`

主目录 ejudge 是通过数据卷的形式挂载在容器内的，所以可以通过 `docker inspect -f {{.Mounts}} YOUR_DOCKER_ID` 的 mount 下的地址找到。
找到该目录的意义，就在于该目录下的 `/run` 便是所有数据的存放、程序运行的位置，另外 `/run/log` 下是程序运行日志。要修改密码，修改配置，也要修改该目录下的 `config` 子目录。
可以加个软链接来快速访问。如果有更简洁的方法，欢迎补充！

### 开发

+ 先创建一个用户：`useradd -r compiler`

+ 拷贝 java policy：`cp sandbox/java_policy /etc/`

+ 安装依赖包（见 Dockerfile）：`pip3 install -r requirements.txt`, `apt-get -y install gcc g++ ...`

+ 编译 Cython：`python3 setup.py build_ext --inplace`

+ 创建目录：`mkdir -p run/data run/sub run/log`

然后就从运行 `tests` 中的测试开始吧。注意在运行 `flask` 测试前要先运行 flask 服务器和 celery：

+ 运行 redis：`service redis-server start`

+ 运行 celery：
    + 阻塞：`celery worker -A handler --loglevel=info`
    + 守护：`celery multi start worker -A handler`

+ 运行 flask：`./flask_server.py`

在生产环境下的命令见 `run.sh`。


## 致谢

eJudge 由 eoj3 团队开发。

eJudge 的设计借（照）鉴（抄）了 [QDUOJ Judger](https://github.com/QingdaoU/Judger/tree/newnew) 中对 seccomp 的使用，
专业出题网站 [Codeforces Polygon](https://polygon.codeforces.com/) 中对测试程序的使用，
开源项目 [testlib](https://github.com/MikeMirzayanov/testlib)
实现的 C++ 库，[UOJ](https://github.com/vfleaking/uoj) 中对 Docker 的使用，
以及 [vijos jd4](https://github.com/vijos/jd4) 中的类设计。

