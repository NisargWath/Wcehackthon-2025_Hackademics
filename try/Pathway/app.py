from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import json
import google.generativeai as genai
from datetime import datetime, timedelta
import random

# Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
generation_config = {
    "temperature": 0.8,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 4096,
}
model = genai.GenerativeModel(model_name="gemini-flash-1.5", generation_config=generation_config)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default-dev-key")

# In-memory database (replace with proper DB in production)
users_db = {}
learning_pathways = {}
progress_data = {}

# Learning resources database
resources = {
    "Machine Learning": {
        "visual": [
            {"type": "video", "title": "Neural Networks Explained Visually", "url": "https://example.com/neural-networks-visual"},
            {"type": "infographic", "title": "Machine Learning Algorithms Comparison", "url": "https://example.com/ml-algorithms-infographic"}
        ],
        "auditory": [
            {"type": "podcast", "title": "Machine Learning Basics Explained", "url": "https://example.com/ml-basics-podcast"},
            {"type": "audio_lecture", "title": "Deep Learning Fundamentals", "url": "https://example.com/deep-learning-audio"}
        ],
        "kinesthetic": [
            {"type": "exercise", "title": "Implement a Simple Neural Network", "url": "https://example.com/neural-network-exercise"},
            {"type": "project", "title": "Build a Recommender System", "url": "https://example.com/recommender-project"}
        ]
    },
    "Web Development": {
        "visual": [
            {"type": "video", "title": "Responsive Web Design", "url": "https://example.com/responsive-design-video"},
            {"type": "infographic", "title": "Front-end Framework Comparison", "url": "https://example.com/frontend-frameworks"}
        ],
        "auditory": [
            {"type": "podcast", "title": "Modern JavaScript Features", "url": "https://example.com/modern-js-podcast"},
            {"type": "audio_lecture", "title": "Web Security Fundamentals", "url": "https://example.com/web-security-audio"}
        ],
        "kinesthetic": [
            {"type": "exercise", "title": "Build a Dynamic Form with Validation", "url": "https://example.com/form-validation-exercise"},
            {"type": "project", "title": "Create a Full-Stack Web Application", "url": "https://example.com/fullstack-project"}
        ]
    },
    "Data Structures": {
        "visual": [
            {"type": "video", "title": "Trees and Graphs Visualized", "url": "https://example.com/trees-graphs-video"},
            {"type": "infographic", "title": "Big-O Complexity Chart", "url": "https://example.com/big-o-chart"}
        ],
        "auditory": [
            {"type": "podcast", "title": "Data Structures Deep Dive", "url": "https://example.com/data-structures-podcast"},
            {"type": "audio_lecture", "title": "Algorithms Analysis", "url": "https://example.com/algorithms-audio"}
        ],
        "kinesthetic": [
            {"type": "exercise", "title": "Implement a Hash Table", "url": "https://example.com/hash-table-exercise"},
            {"type": "project", "title": "Build a Pathfinding Visualizer", "url": "https://example.com/pathfinding-project"}
        ]
    }
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/assessment', methods=['GET', 'POST'])
def assessment():
    if request.method == 'POST':
        # Store assessment data in session
        session['learning_style'] = request.form.get('learning_style')
        session['study_mode'] = request.form.get('study_mode')
        session['time_commitment'] = int(request.form.get('time_commitment'))
        session['motivation_level'] = request.form.get('motivation_level')
        
        # Proceed to subject selection
        return redirect(url_for('subject_selection'))
    
    return render_template('assessment.html')

@app.route('/subject-selection', methods=['GET', 'POST'])
def subject_selection():
    if request.method == 'POST':
        subject = request.form.get('subject')
        session['subject'] = subject
        
        # Generate learning pathway
        generate_pathway(session['learning_style'], session['study_mode'], 
                        session['time_commitment'], session['motivation_level'], subject)
        
        return redirect(url_for('dashboard'))
    
    # List of available subjects
    subjects = ["Machine Learning", "Web Development", "Data Structures"]
    return render_template('subject_selection.html', subjects=subjects)

def generate_pathway(learning_style, study_mode, time_commitment, motivation_level, subject):
    """Generate personalized learning pathway using Gemini AI"""
    user_id = session.get('user_id', str(random.randint(1000, 9999)))
    session['user_id'] = user_id
    
    # Prepare prompt for Gemini
    prompt = f"""
    Create a personalized learning pathway for a student with the following characteristics:
    - Learning Style: {learning_style}
    - Preferred Study Mode: {study_mode}
    - Time Commitment: {time_commitment} hours per week
    - Motivation Level: {motivation_level}
    - Subject: {subject}
    
    The pathway should include:
    1. A weekly breakdown of topics based on {time_commitment} hours per week for 8 weeks
    2. Resource recommendations tailored to {learning_style} learning style
    3. Weekly assessments and progress checks
    4. Gamification elements to maintain engagement
    
    Format the output as JSON with the following structure:
    {
        "subject": "Subject Name",
        "duration_weeks": 8,
        "weekly_plan": [
            {
                "week": 1,
                "topics": ["Topic 1", "Topic 2"],
                "resources": [
                    {"type": "resource_type", "title": "Resource Title", "url": "URL", "duration_minutes": 30}
                ],
                "assessments": [
                    {"title": "Assessment Title", "type": "quiz/project/reflection"}
                ],
                "gamification": {"challenge": "Weekly Challenge", "badge": "Badge Name"}
            }
        ]
    }
    """
    
    try:
        # Call Gemini AI
        response = model.generate_content(prompt)
        
        # Extract and parse JSON from response
        response_text = response.text
        
        # Find JSON content within the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_content = response_text[json_start:json_end]
            pathway = json.loads(json_content)
        else:
            # Fallback if JSON parsing fails
            pathway = generate_fallback_pathway(subject, learning_style, time_commitment)
            
        # Post-process the pathway
        enhance_pathway_with_resources(pathway, subject, learning_style)
        
        # Store the pathway
        learning_pathways[user_id] = pathway
        
        # Initialize progress data
        initialize_progress_data(user_id, pathway)
        
        return pathway
    
    except Exception as e:
        print(f"Error generating pathway: {e}")
        # Fallback if Gemini API fails
        pathway = generate_fallback_pathway(subject, learning_style, time_commitment)
        learning_pathways[user_id] = pathway
        initialize_progress_data(user_id, pathway)
        return pathway

def generate_fallback_pathway(subject, learning_style, time_commitment):
    """Generate a basic fallback pathway if the AI generation fails"""
    # Basic structure for an 8-week course
    pathway = {
        "subject": subject,
        "duration_weeks": 8,
        "weekly_plan": []
    }
    
    # Generic topics for each subject
    topics = {
        "Machine Learning": [
            ["Introduction to ML", "Types of Machine Learning"],
            ["Linear Regression", "Gradient Descent"],
            ["Classification", "Logistic Regression"],
            ["Decision Trees", "Random Forests"],
            ["Neural Networks Basics", "Activation Functions"],
            ["Convolutional Neural Networks", "Image Classification"],
            ["Recurrent Neural Networks", "Natural Language Processing"],
            ["Reinforcement Learning", "ML Ethics and Future"]
        ],
        "Web Development": [
            ["HTML Basics", "CSS Fundamentals"],
            ["JavaScript Essentials", "DOM Manipulation"],
            ["Responsive Design", "CSS Frameworks"],
            ["JavaScript Frameworks Intro", "React Basics"],
            ["React State Management", "Component Lifecycle"],
            ["Backend Basics", "RESTful APIs"],
            ["Database Integration", "Authentication"],
            ["Deployment", "Web Performance Optimization"]
        ],
        "Data Structures": [
            ["Arrays and Strings", "Time and Space Complexity"],
            ["Linked Lists", "Stacks and Queues"],
            ["Hash Tables", "Sets and Maps"],
            ["Trees: Binary Trees", "Binary Search Trees"],
            ["Heaps", "Priority Queues"],
            ["Graphs", "Graph Traversal"],
            ["Sorting Algorithms", "Searching Algorithms"],
            ["Dynamic Programming", "Advanced Problem Solving"]
        ]
    }
    
    # Create weekly plan
    subject_topics = topics.get(subject, [["Basics 1", "Basics 2"]] * 8)
    
    for week in range(8):
        weekly_topics = subject_topics[week] if week < len(subject_topics) else ["Advanced Topic 1", "Advanced Topic 2"]
        
        week_plan = {
            "week": week + 1,
            "topics": weekly_topics,
            "resources": [
                {"type": learning_style, "title": f"{weekly_topics[0]} Resource", 
                 "url": f"https://example.com/{subject.lower().replace(' ', '-')}/{weekly_topics[0].lower().replace(' ', '-')}",
                 "duration_minutes": 30}
            ],
            "assessments": [
                {"title": f"Week {week+1} Quiz", "type": "quiz"},
                {"title": f"Week {week+1} Project", "type": "project"}
            ],
            "gamification": {
                "challenge": f"Complete all Week {week+1} materials",
                "badge": f"Week {week+1} Champion"
            }
        }
        
        pathway["weekly_plan"].append(week_plan)
    
    return pathway

def enhance_pathway_with_resources(pathway, subject, learning_style):
    """Enhance the AI-generated pathway with curated resources from our database"""
    # Get relevant resources for this subject and learning style
    subject_resources = resources.get(subject, {})
    style_resources = subject_resources.get(learning_style.lower(), [])
    
    if not style_resources:
        return pathway
    
    # Add some of our curated resources to the pathway
    for week_plan in pathway["weekly_plan"]:
        # Add 1-2 curated resources that match the learning style
        for resource in style_resources[:2]:
            week_plan["resources"].append({
                "type": resource["type"],
                "title": resource["title"],
                "url": resource["url"],
                "duration_minutes": random.randint(20, 60)
            })
            
    return pathway

def initialize_progress_data(user_id, pathway):
    """Initialize progress tracking data for a user"""
    progress_data[user_id] = {
        "current_week": 1,
        "completion": {
            "resources": {},
            "assessments": {}
        },
        "badges_earned": [],
        "streak_days": 0,
        "last_active": datetime.now().strftime("%Y-%m-%d"),
        "total_points": 0
    }

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id or user_id not in learning_pathways:
        return redirect(url_for('assessment'))
    
    pathway = learning_pathways[user_id]
    progress = progress_data[user_id]
    
    # Get current week's plan
    current_week = progress["current_week"]
    week_plan = next((w for w in pathway["weekly_plan"] if w["week"] == current_week), None)
    
    return render_template('dashboard.html',
                          subject=pathway["subject"],
                          learning_style=session.get('learning_style'),
                          study_mode=session.get('study_mode'),
                          current_week=current_week,
                          total_weeks=pathway["duration_weeks"],
                          week_plan=week_plan,
                          progress=progress)

@app.route('/mark-complete', methods=['POST'])
def mark_complete():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
    
    data = request.json
    item_type = data.get('type')  # 'resource' or 'assessment'
    item_id = data.get('id')
    
    if not item_type or not item_id:
        return jsonify({"error": "Missing parameters"}), 400
    
    # Update completion status
    if item_type == 'resource':
        progress_data[user_id]["completion"]["resources"][item_id] = True
        progress_data[user_id]["total_points"] += 10
    elif item_type == 'assessment':
        progress_data[user_id]["completion"]["assessments"][item_id] = True
        progress_data[user_id]["total_points"] += 20
    
    # Update streak
    today = datetime.now().strftime("%Y-%m-%d")
    last_active = datetime.strptime(progress_data[user_id]["last_active"], "%Y-%m-%d")
    if (datetime.now() - last_active).days <= 1:
        progress_data[user_id]["streak_days"] += 1
    else:
        progress_data[user_id]["streak_days"] = 1
    progress_data[user_id]["last_active"] = today
    
    # Check if week is complete
    check_week_completion(user_id)
    
    return jsonify({"success": True, "points": progress_data[user_id]["total_points"]})

def check_week_completion(user_id):
    """Check if current week is complete and award badges"""
    pathway = learning_pathways[user_id]
    progress = progress_data[user_id]
    current_week = progress["current_week"]
    
    # Get current week's plan
    week_plan = next((w for w in pathway["weekly_plan"] if w["week"] == current_week), None)
    if not week_plan:
        return
    
    # Check if all resources and assessments are complete
    resources_complete = True
    for i, resource in enumerate(week_plan["resources"]):
        resource_id = f"week{current_week}_resource{i}"
        if resource_id not in progress["completion"]["resources"]:
            resources_complete = False
            break
    
    assessments_complete = True
    for i, assessment in enumerate(week_plan["assessments"]):
        assessment_id = f"week{current_week}_assessment{i}"
        if assessment_id not in progress["completion"]["assessments"]:
            assessments_complete = False
            break
    
    # If week is complete, award badge and move to next week
    if resources_complete and assessments_complete:
        badge = week_plan["gamification"]["badge"]
        if badge not in progress["badges_earned"]:
            progress["badges_earned"].append(badge)
            progress["total_points"] += 50
        
        # Move to next week if not already at the end
        if current_week < pathway["duration_weeks"]:
            progress["current_week"] += 1

@app.route('/update-learning-preferences', methods=['POST'])
def update_learning_preferences():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
    
    # Update session with new preferences
    session['learning_style'] = request.form.get('learning_style', session.get('learning_style'))
    session['study_mode'] = request.form.get('study_mode', session.get('study_mode'))
    session['time_commitment'] = int(request.form.get('time_commitment', session.get('time_commitment')))
    session['motivation_level'] = request.form.get('motivation_level', session.get('motivation_level'))
    
    # Regenerate pathway with updated preferences
    subject = learning_pathways[user_id]["subject"]
    generate_pathway(session['learning_style'], session['study_mode'], 
                    session['time_commitment'], session['motivation_level'], subject)
    
    return redirect(url_for('dashboard'))

@app.route('/get-recommendations', methods=['POST'])
def get_recommendations():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
    
    # Get current performance data
    difficulty_rating = int(request.form.get('difficulty_rating', 3))
    interest_rating = int(request.form.get('interest_rating', 3))
    
    # Use Gemini to generate adaptive recommendations
    prompt = f"""
    Based on the following user feedback:
    - Difficulty Level (1-5): {difficulty_rating} (5 being very difficult)
    - Interest Level (1-5): {interest_rating} (5 being very interesting)
    - Learning Style: {session.get('learning_style')}
    
    Generate 1-2 adaptive recommendations to better support this learner studying 
    {learning_pathways[user_id]["subject"]} in week {progress_data[user_id]["current_week"]}.
    
    Format the output as a JSON list of recommendations:
    [
        {{"recommendation": "Specific advice", "resource": "Additional resource name", "url": "URL"}}
    ]
    """
    
    try:
        # Call Gemini AI
        response = model.generate_content(prompt)
        
        # Extract and parse JSON from response
        response_text = response.text
        
        # Find JSON content within the response
        json_start = response_text.find('[')
        json_end = response_text.rfind(']') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_content = response_text[json_start:json_end]
            recommendations = json.loads(json_content)
        else:
            # Fallback if JSON parsing fails
            recommendations = [
                {"recommendation": "Try breaking down the content into smaller chunks", 
                 "resource": "Study techniques for complex topics", 
                 "url": "https://example.com/study-techniques"}
            ]
            
        return jsonify({"recommendations": recommendations})
    
    except Exception as e:
        print(f"Error generating recommendations: {e}")
        # Fallback recommendations
        recommendations = [
            {"recommendation": "Review foundational concepts before proceeding", 
             "resource": "Fundamentals review", 
             "url": "https://example.com/fundamentals"}
        ]
        return jsonify({"recommendations": recommendations})

if __name__ == '__main__':
    app.run(debug=True, port=8000)