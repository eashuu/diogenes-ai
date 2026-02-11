import os
from horde_sdk.ai_horde_api.ai_horde_clients import AIHordeAPISimpleClient
from horde_sdk.ai_horde_api.apimodels.generate._async import ImageGenerateAsyncRequest
from horde_sdk.ai_horde_api.apimodels.generate._status import ImageGenerateStatusResponse

API_KEY = os.getenv("AIHORDE_API_KEY", "VnnujNbuKSCrWKkTv1Xidg")  # use your key, or anonymous

def main():
    prompt = "a cozy cabin in a snowy forest at sunset, cinematic lighting"
    client = AIHordeAPISimpleClient()

    status_response, job_id = client.image_generate_request(
        ImageGenerateAsyncRequest(
            apikey=API_KEY,
            prompt=prompt,
            models=["Deliberate"],  # change if you prefer a different model
        )
    )

      # Download the first generated image
    image = client.download_image_from_generation(status_response.generations[0])
    image.save("horde_output.png")
    print("Saved: horde_output.png")

if __name__ == "__main__":
    main()