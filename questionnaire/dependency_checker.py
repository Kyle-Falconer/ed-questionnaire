from questionnaire.models import Question, Answer
import logging


def check_actual_answers_against_expression(check_answer, actual_answer, check_question):

   # Numeric Value Expressions
    if check_answer[0:1] in "<>":
        try:
            actual_answer = float(actual_answer)
            if check_answer[1:2] == "=":
                check_value = float(check_answer[2:])
            else:
                check_value = float(check_answer[1:])
        except:
            logging.error("ERROR: must use numeric values with < <= => > checks (%r)" % check_question)
            return False
        if check_answer.startswith("<="):
            return actual_answer <= check_value
        if check_answer.startswith(">="):
            return actual_answer >= check_value
        if check_answer.startswith("<"):
            return actual_answer < check_value
        if check_answer.startswith(">"):
            return actual_answer > check_value

    # Convert answer to list if not already one
    if type(actual_answer) != type(list()):
        actual_answer = [actual_answer]

    # Negative Value Expressions
    if check_answer.startswith("!"):
        for actual_answer in actual_answer:
            if actual_answer == '':
                return False
            if check_answer[1:].strip() == actual_answer.strip():
                return False
            return True
        return

    # Positive Value Expressions
    for actual_answer in actual_answer:
        if check_answer.strip() == actual_answer.strip():
            return True
        return False


def dep_check(expr, runinfo, answerdict):
    """
    Given a comma separated question number and expression, determine if the
    provided answer to the question number satisfies the expression.

    If the expression starts with >, >=, <, or <=, compare the rest of
    the expression numerically and return False if it's not able to be
    converted to an integer.

    If the expression starts with !, return true if the rest of the expression
    does not match the answer.

    Otherwise return true if the expression matches the answer.

    If there is no comma and only a question number, it checks if the answer
    is "yes"

    When looking up the answer, it first checks if it's in the answerdict,
    then it checks runinfo's cookies, then it does a database lookup to find
    the answer.

    The use of the comma separator is purely historical.
    """

    if hasattr(runinfo, 'questionset'):
        questionnaire = runinfo.questionset.questionnaire
    elif hasattr(runinfo, 'questionnaire'):
        questionnaire = runinfo.questionnaire
    else:
        assert False

    # Parse expression
    if "," not in expr:
        expr = expr + ",yes"

    check_questionnum, check_answer = expr.split(",", 1)

    # Get question to check
    try:
        check_question = Question.objects.get(number=check_questionnum,
                                              questionset__questionnaire=questionnaire)
    except Question.DoesNotExist:
        return False

    # Parse & load actual answer(s) from user
    if check_question in answerdict:
        # test for membership in multiple choice questions
        # FIXME: only checking answerdict
        for k, v in answerdict[check_question].items():
            if not k.startswith('multiple_'):
                continue
            if check_answer.startswith("!"):
                if check_answer[1:].strip() == v.strip():
                    return False
            elif check_answer.strip() == v.strip():
                return True
        actual_answer = answerdict[check_question].get('ANSWER', '')
    elif hasattr(runinfo, 'get_cookie') and runinfo.get_cookie(check_questionnum, False):
        actual_answer = runinfo.get_cookie(check_questionnum)
    else:
        # retrieve from database
        ansobj = Answer.objects.filter(question=check_question,
                                       runid=runinfo.runid, subject=runinfo.subject)
        if ansobj:
            actual_answer = ansobj[0].split_answer()[0]
            logging.warn("Put `store` in checks field for question %s" % check_questionnum)
        else:
            actual_answer = None

    if not actual_answer:
        if check_question.getcheckdict():
            actual_answer = check_question.getcheckdict().get('default')

    if actual_answer is None:
        actual_answer = u''
    if type(actual_answer) == type(list()):
       actual_answer = actual_answer[0]

    return check_actual_answers_against_expression(check_answer, actual_answer, check_question)
