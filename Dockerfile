FROM node:8 as yarn

RUN mkdir /static
WORKDIR /static
COPY ./static/.bowerrc ./static/bower.json ./static/package.json ./static/yarn.lock ./
RUN yarn install --production=true --frozen-lockfile

FROM yarn as gulp

RUN yarn install --frozen-lockfile
COPY ./static/ ./
RUN yarn build

FROM python:3.7 as base

RUN apt update && apt install -y openjdk-11-jre-headless && apt clean

WORKDIR /eoj3
COPY ./requirements.txt  ./
RUN pip3 install --no-cache-dir -r requirements.txt
COPY --from=yarn /static/ ./static
COPY --from=gulp /static/css/ ./static/css
COPY .  ./

EXPOSE 80
EXPOSE 3031

WORKDIR /eoj3