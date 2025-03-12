import json
import boto3

bedrock = boto3.client(service_name='bedrock-runtime')
ssm = boto3.client(service_name='ssm')
aws_region="us-east-1"
bastion_ec2="i-xxxxxxxxxxxx"

def lambda_handler(event, context):
  print("This lambda function is going to create or modify AWS Resources.")
  
  actionGroup = event['actionGroup']
  function = event['function']
  inputText = event["inputText"]

  bedrock_response = bedrock.invoke_model(
    modelId="anthropic.claude-3-haiku-20240307-v1:0",
    body = json.dumps({
        'system': f'You are an expert in AWS CLI Commands. You must convert the natural language input into an AWS CLI commands. Your output must be a shell script. Do not write any comments. You must specify a region {aws_region}.',
        'anthropic_version': 'bedrock-2023-05-31',
        'messages': [ { 'role': 'user', 'content': inputText } ],
        'max_tokens': 2048,
        'temperature': 0.5
    }),
    accept='application/json', 
    contentType='application/json'
  )
  shell_script = json.loads(bedrock_response.get('body').read())['content'][0]['text']
  print(f"Running Following Shell Script: {shell_script}")
  ssm_response = ssm.send_command(
    InstanceIds=[
        bastion_ec2
    ],
    DocumentName='AWS-RunShellScript',
    Parameters={
        'commands': [
            shell_script
        ]
    }
  )
  ssm_command_id = ssm_response["Command"]["CommandId"]
  waiter = ssm.get_waiter('command_executed')
  try:
    waiter.wait(
        CommandId=ssm_command_id,
        InstanceId=bastion_ec2
    )
  except:
    print("Error")
  ssm_result = ssm.get_command_invocation(
    CommandId=ssm_command_id,
    InstanceId=bastion_ec2
  )
  status_detail = ssm_result["StatusDetails"]

  # https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html
  responseBody =  {
    "TEXT": {
      "body": f"Running Shell Script Status : {status_detail}"
    }
  }

  action_response = {
    'actionGroup': actionGroup,
    'function': function,
    'functionResponse': {
      'responseBody': responseBody
    }
  }

  lambda_function_response = {'response': action_response, 'messageVersion': event['messageVersion']}
  print("Response: {}".format(lambda_function_response))

  return lambda_function_response