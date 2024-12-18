import json
import torch
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm

model_name = "d0rj/e5-base-en-ru" 
json_file_path = 'dataset/gazprom_dataset.json'
output_file_path = 'vector_e5-base-en-ru.json'

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

if torch.cuda.is_available():
    print("Используется GPU для вычислений")
else:
    print("Используется CPU для вычислений")

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name).to(device)

def get_vector(text):
    """Получает векторное представление текста с использованием модели."""
    if not text or text.strip() == "":
        return torch.zeros(768)

    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        vector = outputs.last_hidden_state.mean(dim=1)

    return vector.squeeze().cpu().numpy()

def filter_by_keywords(content, keywords_or_phrases):
    """Фильтрует контент по ключевым словам и фразам."""
    matched_keywords = []
    
    if keywords_or_phrases is None:
        keywords_or_phrases = []
    
    for keyword_info in keywords_or_phrases:
        keyword = keyword_info.get('keyword_or_phrase', '')
        if keyword:
            keyword = keyword.lower()
            if keyword in content.lower():
                matched_keywords.append(keyword)
    
    return matched_keywords

def load_and_vectorize_dataset(json_file_path, output_file_path):
    """Загружает и векторизует датасет, сохраняя результат в файл."""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result_data = []

    for entry in tqdm(data, desc="Обработка данных", unit="entry"):
        content = entry.get('content', None)
        chunk_id = entry.get('chunk_id', '')
        keywords_or_phrases = entry.get('keywords_or_phrases', [])

        if content is None:
            continue

        # Приводим ключевые слова в entry к нижнему регистру
        keywords_or_phrases = keywords_or_phrases if keywords_or_phrases else []
        normalized_keywords_or_phrases = [
            {'keyword_or_phrase': k['keyword_or_phrase'].lower()} 
            for k in keywords_or_phrases 
            if 'keyword_or_phrase' in k and k['keyword_or_phrase']
        ]


        content_vector = get_vector(content)
        matched_keywords = filter_by_keywords(content, normalized_keywords_or_phrases)
        result_data.append({
            'chunk_id': chunk_id,
            'content': content,
            'keywords': matched_keywords,
            'content_vector': content_vector.tolist()
        })

    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)

    print(f"Векторизация завершена. Все данные сохранены в файл: {output_file_path}")

if __name__ == "__main__":
    load_and_vectorize_dataset(json_file_path, output_file_path)
