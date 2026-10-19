docker build -t docker_digits .

docker save docker_digits > digits_train.tar

docker run docker_digits
