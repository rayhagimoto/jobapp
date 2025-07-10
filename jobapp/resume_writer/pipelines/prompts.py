# --- 
# Keywords
# ---

SkillsAndQualificationsPrompt = """You are an expert resume writer. Your primary goal is to help me optimize my resume for a {job_title} job description which I will provide you. Analyze it and identify what key skills, technologies, and short phrases the job description requires. Your response must be a YAML-formatted list of keywords and key phrases, under the field KEYWORDS.

**MANDATORY OUTPUT FORMAT:**
Your entire response must be a single YAML code block, and nothing else. Do not add any commentary, explanations, or markdown outside the code block.

Each item in the list should be a single skill, technology, or short phrase (2-5 words max) that is a core requirement or strong preference in the job description. Do not include full sentences, soft skills, or generic statements unless they are explicitly required in the job description. Do not repeat keywords. Follow the job description's convention for capitalization, for all keywords unless they are proper nouns.
The keyword list should be divided into 'required', 'preferred', and 'nice to have' where the required skills are the absolutely core, fundamental skills, someone in this position must have. 
'Preferred' skills refer to those skills which would set the candidate apart. 'Nice to have' are less crucial to put on the resume, and should be given less priority.

**JOB DESCRIPTION**
{job_description}

**EXAMPLE OUTPUT:**
```yaml
keywords:
  required:
    - 'python [9]'
    - 'machine learning [9]'
    - 'advanced AI expertise'
  preferred:
    - 'AWS [9]'
    - 'data visualization [9]'
    - 'statistical modeling [3]'
  nice_to_have:
    - 'team collaboration [4]'
```

**DO NOT:**
- Do NOT include any text outside the YAML code block.
- Do NOT include explanations, summaries, or markdown headings.
- Do NOT include full sentences as keywords.
- Do NOT repeat keywords.
- Do NOT include generic statements unless explicitly required.

**IMPORTANT: Provide only the analysis. Do not ask questions, suggest next steps, or offer additional services. Focus solely on identifying the key skills.**"""

# --- 
# Profile and skills prompt
# ---

ProfileAndSkillsPrompt = """You are an expert resume writer. Your goal is to help me write a profile description that is targeted to a specific job description, and update my skills list to emphasize the most relevant skills I show evidence of which are related to the job. I will provide you with my full resume, and an account of my experiences. Compare your analysis with my resume and experiences, identify where my background (i) directly (ii) partially align with the qualifications and skills and use this analysis to update my profile description and skills list. 

Here is my resume: 
{resume}

Here is an account of my experiences:
{experiences}

The profile should be concise (up to 90 words), professional, and demonstrate a keen interest in the role (e.g. last sentence says Eager to apply quantitative expertise in...). Being specific and true to the candidate's experiences is more useful than using more vague and broad language by itself. For example while it's good to say the candidate has experience with 'machine learning' it is better to tie this to an explicit example to better communicate the type of machine learning, e.g. decision trees, and convolutional neural networks. For jobs that are related to finance it makes sense to frontload the quantitative finance research experience, but for non-finance jobs it makes sense to devote less words to the finance side, and emphasize the more transferable predictive modeling skills in an industry setting from a quantitative finance internship. One example of an accurate statement is "5 years of experience leveraging statistical methods for data analysis in Python, with internship experience in quantitative finance". You should strategically choose to include keywords in a way that doesn't diminish specificity too much. 

**For Skills List Generation:**
*   **Prioritize direct matches and strong alignment:** Identify skills and technologies mentioned explicitly in the job description that directly align with the candidate's experience.
*   **Balance generality with specificity:** For broad categories or algorithms mentioned in the job description (e.g., 'Machine Learning,' 'Statistical Methodology,' 'Gradient Boosting Trees'), include the general term. **However, if the candidate has specific, impactful experience with a widely recognized subset or implementation of that general category (e.g., 'LightGBM' under 'Gradient Boosting Trees', or 'Linear Regression' under 'GLM/Regression'), include both the general term and the specific example if space allows and the example significantly strengthens the candidate's profile.**
*   **Translate implementations to general categories if listed in JD:** If the job description lists a general algorithm (e.g., 'Gradient Boosting Trees') and your experience uses a specific implementation (e.g., 'LightGBM'), include the general algorithm from the JD in the skills list. Where appropriate and space permits, also include the specific implementation to demonstrate depth.
*   **Emphasize key tools/languages:** Always include core programming languages (e.g., Python, R, SAS) and essential tools (e.g., SQL, Git) if they are explicitly mentioned or clearly implied by the job description and supported by the candidate's experience.
*   **Select most pertinent skills:** Choose 10-15 most pertinent skills for the role, prioritizing those where the candidate has multiple projects or significant depth of experience, especially if they align closely with job description keywords.

**Mandatory output format:**
(one mardown block, two separate yaml blocks.)

```markdown
your analysis goes here
```

```yaml
profile:
  description: 'Description goes here'
  # old_description: 'Old description goes here'
```

```yaml
skills:
  - Skill 1
  - Skill 2
  ...
  - Skill 15
"""