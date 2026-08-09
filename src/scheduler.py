from datetime import datetime,date

def calculate_subject_priorities(enrollments,db_session,subject_model,topic_model,global_exam_start):
    """
    OS-Inspired Scheduler: Computes priority weights for active subjects
    based on  deadline (EDF), remaining topics, and urgency.
    """
    scheduled_processes = []

    for enr in enrollments:
        sub = db_session.query(subject_model).filter(subject_model.id == enr.subject_id).first()
        if not sub:
            continue

        #get topic status
        topics = db_session.query(topic_model).filter(topic_model.subject_id == sub.id).all()
        total_topics = len(topics)
        covered_topics = sum(1 for t in topics if t.is_covered)
        remaining_topics = total_topics - covered_topics

        # Determine effective exam date (Individual date takes precedence; fallback to global block window)
        effective_date = global_exam_start
        is_individual_date = False
        
        if enr.exam_date and enr.exam_date != "None":
            try:
                effective_date = datetime.strptime(enr.exam_date, "%Y-%m-%d").date()
                is_individual_date = True
            except:
                pass

        #calculate deadline(days left)
        days_left = (effective_date - date.today()).days
        
        if days_left <= 0:
            urgency_score = 9999
        else:
            urgency_score = (remaining_topics * 10)/days_left
        
        scheduled_processes.append({
            "sub_obj": sub,                # The database subject object
            "subject_id": sub.id,
            "name": sub.name,
            "category": sub.category,
            "total_topics": total_topics,
            "covered_topics": covered_topics,
            "remaining_topics": remaining_topics,
            "effective_date": effective_date,
            "is_individual": is_individual_date,
            "days_left": days_left,
            "priority_weight": urgency_score
        })

        scheduled_processes = sorted(scheduled_processes,key = lambda x:x["priority_weight"],reverse=True)

        return scheduled_processes