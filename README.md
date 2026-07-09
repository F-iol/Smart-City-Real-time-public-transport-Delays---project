## AWS Lambda problem

Planned on using AWS lambda for ingestion process , I set it up but AWS was unable to retrieve any data from the Warsaw's API due to repeated timeouts <br>
Issue appears to be related to inaccessible API while using AWS enviroment possibly due to Warsaw's API filtering.  
Since it worked locally I switched to more suitable approach to ingest data and upload it to S3 manually via ```ingestion.py```
