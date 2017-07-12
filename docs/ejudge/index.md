# eJudge

## 简介

eJudge 是 eoj3 捆绑销售的判题服务器。主要职责是提供判题服务（废话）。设计判题服务器的主要意图有二：

- 负载均衡：可以根据比赛需求添加减少判题服务器，在节省资源的同时，保证判题速度。
- 运行安全：提交的代码是不受信任的。在单独的判题服务器中运行方便意外情况的处理。

此外，相比其他 OJ 判题服务器，eJudge 还具有以下特色：

- 使用 Docker 急速部署，方便重启。
- 判题服务提供了 socket.io 和 RESTful API 两种方式，方便判题进程的即时响应及更新。
- 支持 generator, validator, stress test 等测试工具的运行，为 Polygon system 提供支持（开发中）。

## 判题服务器设计

为方便读者理解，这里对每个类的设计初衷进行解释。

### 测试用例 (Case)

每一个测试用例都有一个**指纹** (fingerprint)，这一指纹在上传测试用例的时候就已经指定。
需要注意的是，指定指纹的时候应尽可能避免使用 32 位纯字母指纹，避免冲突（虽然冲突概率非常低）。

测试用例含 input 和 output，分别为输入和输出。如果只有 input，那就不能称为测试用例，即使上传 input 也只会带来异常。
要根据 input 生成 output 需要调用另外的 API。

### 程序 (Submission)

所有在判题服务器上运行的程序的基类。Submission 本身提供了运行（run）方法，默认开启沙盒运行。

所有程序都有一个**指纹** (fingerprint)，如何获得指纹判题服务器不关心，但应确保唯一。受信任程序是可以永久保存的，
对于受信任程序而言，指纹尤其重要，因为每一个判题请求都需要指定对应的输出检查器，这种指定就是通过指纹来实现的。

### 受信任程序 (TrustedSubmission)

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

## 文档局限性

这里的文档面向正在开发中的 ejudge v2。v1（目前 master 分支）的文档不再更新。

## 安装

### 部署

### 开发

`python3 setup.py build_ext --inplace`


## 致谢

eJudge 的设计借（照）鉴（抄）了 [QDUOJ Judger](https://github.com/QingdaoU/Judger/tree/newnew) 中对 seccomp 的使用，
专业出题网站 [Codeforces Polygon](https://polygon.codeforces.com/) 中对测试程序的使用，
开源项目 [testlib](https://github.com/MikeMirzayanov/testlib)
实现的 C++ 库，[UOJ](https://github.com/vfleaking/uoj) 中对 Docker 的使用，
以及 [vijos jd4](https://github.com/vijos/jd4) 中的类设计。

