# -*- coding: utf-8 -*-
"""Stable Diffusion

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1RL2lbgqn3dI8PKURU6YuMz9zFjWbB0Bc
"""

!pip install diffusers transformers accelerate datasets torch torchvision

import torch
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

transform = transforms.Compose([
    transforms.Grayscale(num_output_channels=3),  # Convert to 3-channel RGB
    transforms.Resize((512, 512)),                # Resize to 512x512 pixels
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])  # Normalize
])
mnist_dataset = datasets.MNIST(root="mnist_data", train=True, download=True, transform=transform)
mnist_dataloader = DataLoader(mnist_dataset, batch_size=16, shuffle=True)

from diffusers import StableDiffusionPipeline, DDPMScheduler
from transformers import CLIPTextModel, CLIPTokenizer
import torch

# Load pre-trained Stable Diffusion model
model_id = "runwayml/stable-diffusion-v1-5"
pipe = StableDiffusionPipeline.from_pretrained(model_id)
pipe.to("cuda")

# Replace scheduler with DDPMScheduler for training
pipe.scheduler = DDPMScheduler.from_config(pipe.scheduler.config)

# Extract components
unet = pipe.unet
vae = pipe.vae
text_encoder = pipe.text_encoder
tokenizer = pipe.tokenizer

# Optimizer
optimizer = torch.optim.AdamW(unet.parameters(), lr=1e-4)

# Training loop
num_epochs = 1
device = "cuda"
unet.train()

for epoch in range(num_epochs):
    for step, (images, labels) in enumerate(mnist_dataloader):
        # Prepare images
        pixel_values = images.to(device)

        # Encode images to latents
        latents = vae.encode(pixel_values).latent_dist.sample()
        latents = latents * vae.config.scaling_factor

        # Add noise to latents
        noise = torch.randn_like(latents)
        timesteps = torch.randint(0, pipe.scheduler.num_train_timesteps, (latents.size(0),), device=device).long()
        noisy_latents = pipe.scheduler.add_noise(latents, noise, timesteps)

        # Prepare text embeddings
        prompts = [f"a photo of the number {label}" for label in labels]
        inputs = tokenizer(prompts, return_tensors="pt", padding="max_length", truncation=True, max_length=77)
        input_ids = inputs["input_ids"].to(device)
        encoder_hidden_states = text_encoder(input_ids).last_hidden_state

        # Predict noise
        noise_pred = unet(noisy_latents, timesteps, encoder_hidden_states).sample

        # Compute loss
        loss = torch.nn.functional.mse_loss(noise_pred, noise)

        # Backpropagation
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if step % 100 == 0:
            print(f"Epoch {epoch + 1}, Step {step}, Loss: {loss.item()}")

# Save the fine-tuned model
pipe.save_pretrained("stable_diffusion_mnist")

from diffusers import StableDiffusionPipeline

# Load the fine-tuned model
pipe = StableDiffusionPipeline.from_pretrained("stable_diffusion_mnist")
pipe.to("cuda")

# Generate a new MNIST-style image
prompt = "a handwritten digit"
image = pipe(prompt).images[0]

# Display the image
image.show()