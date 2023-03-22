#python image
FROM python:3.11-slim-bullseye
#copy everything from app into curr dir of container
COPY /app .
RUN pip3 install -r requirements.txt
EXPOSE 5000