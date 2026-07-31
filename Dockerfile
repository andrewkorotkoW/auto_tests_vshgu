FROM git.devspark.ru:5005/devops/docker/images/python:3.12-slim

# USER user

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["pytest"]

CMD ["-v", "--tb=short"]