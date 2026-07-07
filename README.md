1 - CEO :

1. לייצר AGENT.MD
2. לייצר SKILL.MD
3. לייצר תיקיות רלוונטיות
4. לרשום פרומפט מפורט - פרומפט לדוגמא
5. לעדכן את הCEO

6. עובד חדש (לדוגמה):
7. לייצר AGENT.MD
8. לייצר SKILL.MD:

9. לייצר תיקיות רלוונטיות
10. לרשום פרומפט מפורט - :

יש ליצור סוכן חדש בתןך
\.claude\agents
ואז את הסקיל פה :
\.claude\skills

curl -X POST "https://api.openai.com/v1/images/generations" \
 -H "Authorization: Bearer $OPENAI_API_KEY" \
 -H "Content-Type: application/json" \
 -d '{
"model": "gpt-image-2",
"prompt": "A cinematic image of a futuristic AI agent workspace",
"size": "1024x1024",
"quality": "medium",
"output_format": "png"
}' | jq -r '.data[0].b64_json' | base64 --decode > image.png

5. לעדכן את הCEO

6. עובד חדש נוסף (לדוגמה):
7. לייצר AGENT.MD
8. לייצר SKILL.MD
9. לייצר תיקיות רלוונטיות
10. לרשום פרומפט מפורט
11. לעדכן את הCEO
