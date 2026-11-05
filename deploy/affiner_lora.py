"""
Affinage LoRA du modèle local d'IA AISSA sur ses corrections validées — à lancer sur un serveur avec carte graphique
(jamais sur Streamlit Cloud). Étapes complètes dans deploy/README.md, section « Affiner le modèle local (LoRA) ».

    pip install "transformers>=4.45" "peft>=0.13" accelerate datasets
    python -m ia_aissa.affinage exporter affinage.jsonl                 # le jeu d'affinage, depuis la base
    python -m ia_aissa.affinage mesurer --modele qwen2.5:3b             # mesure AVANT
    python deploy/affiner_lora.py affinage.jsonl --sortie ia-aissa-lora
    # conversion en GGUF (llama.cpp), puis : ollama create ia-aissa-local -f deploy/Modelfile.lora
    python -m ia_aissa.affinage mesurer --modele ia-aissa-local         # mesure APRÈS (même jeu de questions)

Seules les réponses de l'assistant comptent dans la perte (la consigne, les sources et la question sont masquées) :
le modèle apprend à répondre à partir des SOURCES, pas à réciter la consigne.
"""

import argparse
import json


def charger(chemin):
    with open(chemin, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def tokeniser(tokenizer, exemple, longueur_max):
    """input_ids et labels : -100 partout sauf sur la réponse de l'assistant."""
    messages = exemple["messages"]
    debut = tokenizer.apply_chat_template(messages[:-1], tokenize=True, add_generation_prompt=True)
    complet = tokenizer.apply_chat_template(messages, tokenize=True)[:longueur_max]
    labels = [-100] * min(len(debut), len(complet)) + complet[len(debut):]
    return {"input_ids": complet, "labels": labels[:len(complet)], "attention_mask": [1] * len(complet)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jeu", help="fichier JSONL produit par « python -m ia_aissa.affinage exporter »")
    parser.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct", help="le même modèle que celui servi par Ollama")
    parser.add_argument("--sortie", default="ia-aissa-lora")
    parser.add_argument("--epoques", type=int, default=3)
    parser.add_argument("--rang", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--longueur-max", type=int, default=1024)
    args = parser.parse_args()

    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model
    from transformers import (AutoModelForCausalLM, AutoTokenizer, DataCollatorForSeq2Seq, Trainer,
                              TrainingArguments)

    tokenizer = AutoTokenizer.from_pretrained(args.base)
    modele = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=torch.bfloat16, device_map="auto")
    modele = get_peft_model(modele, LoraConfig(r=args.rang, lora_alpha=2 * args.rang, lora_dropout=0.05,
                                               target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                                               task_type="CAUSAL_LM"))
    modele.print_trainable_parameters()
    exemples = [tokeniser(tokenizer, e, args.longueur_max) for e in charger(args.jeu)]
    print(f"{len(exemples)} exemples")
    Trainer(model=modele, train_dataset=Dataset.from_list(exemples),
            data_collator=DataCollatorForSeq2Seq(tokenizer, padding=True, label_pad_token_id=-100),
            args=TrainingArguments(output_dir=args.sortie, num_train_epochs=args.epoques, learning_rate=args.lr,
                                   per_device_train_batch_size=4, gradient_accumulation_steps=2, logging_steps=5,
                                   save_strategy="no", bf16=True, report_to=[])).train()
    fusionne = modele.merge_and_unload()                     # adaptateur fusionné : un modèle complet à convertir
    fusionne.save_pretrained(f"{args.sortie}/fusionne", safe_serialization=True)
    tokenizer.save_pretrained(f"{args.sortie}/fusionne")
    print(f"Modèle fusionné : {args.sortie}/fusionne — convertissez-le en GGUF (llama.cpp) puis « ollama create ».")


if __name__ == "__main__":
    main()
