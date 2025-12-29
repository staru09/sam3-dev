import requests

with open("video1.mp4", "rb") as f:
    response = requests.post(
        "http://localhost:8000/segment/dog",
        files={"video": f},
        data={"background_mode": "black"}
    )

# First, check the status code
print(f"Status Code: {response.status_code}")

# Print the full response to see what's happening
result = response.json()
print(f"Full Response: {result}")

# Now safely access the output
if response.status_code == 200 and result.get('success'):
    print(f"Output: {result['output_video_path']}")
else:
    # There was an error - print the details
    if 'detail' in result:
        print(f"Error: {result['detail']}")
    elif 'message' in result:
        print(f"Message: {result['message']}")

