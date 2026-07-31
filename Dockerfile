FROM git.devspark.ru:5005/devops/docker/images/python:3.14.6-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["pytest"]

CMD ["-v", "--tb=short"]