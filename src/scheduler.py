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

        if total_topics > 0:

            #average confidence percentage calcluation
            total_confidence = sum(t.confidence_score for t in topics)

            max_possible_confidence = total_topics*10
            readiness_score = int((total_confidence / max_possible_confidence) * 100) if max_possible_confidence > 0 else 0.0

            #count topics needing attention
            pending_or_low_confidence_topics = sum(1 for t in topics if t.confidence_score < 7)
        else:
            readiness_score = 0
            pending_or_low_confidence_topics = 0 

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
        
        #if days_left <= 0:
        #    urgency_score = 9999
        #else:
        #    urgency_score = (remaining_topics * 10)/days_left
        
        scheduled_processes.append({
            "sub_obj": sub,
            "subject_id": sub.id,
            "name": sub.name,
            "category": sub.category,
            "total_topics": total_topics,
            "covered_topics": total_topics - pending_or_low_confidence_topics, # Approximation for display compatibility
            "remaining_topics": pending_or_low_confidence_topics,
            "readiness_score": readiness_score,
            "effective_date": effective_date,
            "is_individual": is_individual_date,
            "days_left": days_left
        })

    scheduled_processes.sort(key = lambda x: (x["days_left"], -x["remaining_topics"]))

    return scheduled_processes