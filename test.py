from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model_name = "PygmalionAI/pygmalion-2-13b"
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Для GPU с 8+ ГБ VRAM (настройки под RTX)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    load_in_4bit=True,  # Оптимизация под GPU
    torch_dtype=torch.float16
)

def generate_text(prompt):
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=50)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

print(generate_text("Привет, как твои дела?"))
