FROM mysql:8.0

# 日本語対応の文字セット設定
RUN echo '[mysqld]\n\
character-set-server=utf8mb4\n\
collation-server=utf8mb4_unicode_ci\n\
\n\
[client]\n\
default-character-set=utf8mb4' > /etc/mysql/conf.d/charset.cnf
