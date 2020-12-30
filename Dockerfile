#FROM ghcr.io/tripl-ai/arc::latest
FROM ghcr.io/tripl-ai/arc:arc_3.6.2_spark_3.0.1_scala_2.12_hadoop_3.2.0_1.16.0
ENV SPARK_HOME /opt/spark
RUN mkdir -p $SPARK_HOME/work-dir
WORKDIR $SPARK_HOME/work-dir
COPY source/app_resources/driver-pod-template.yaml ./
COPY source/app_resources/executor-pod-template.yaml ./