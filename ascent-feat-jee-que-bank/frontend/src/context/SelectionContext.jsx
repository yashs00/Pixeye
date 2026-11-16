import React, { createContext, useContext, useState, useEffect } from 'react';
import { selectionApi } from '../services/api';

const SelectionContext = createContext();

export function SelectionProvider({ children }) {
  const sessionId = 'teacher-session';
  const [selectedQuestions, setSelectedQuestions] = useState(() => {
    try {
      const saved = localStorage.getItem('ascent_selected_questions');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Save to localStorage on change
  useEffect(() => {
    try {
      localStorage.setItem('ascent_selected_questions', JSON.stringify(selectedQuestions));
    } catch (e) {
      console.error('Failed to sync selection to localStorage', e);
    }
  }, [selectedQuestions]);

  const isSelected = (questionId) => {
    return selectedQuestions.some((q) => q.id === questionId);
  };

  const toggleQuestion = (question) => {
    setSelectedQuestions((prev) => {
      const exists = prev.some((q) => q.id === question.id);
      if (exists) {
        // Remove locally and sync backend
        selectionApi.removeSelection(sessionId, question.id).catch(console.error);
        return prev.filter((q) => q.id !== question.id);
      } else {
        // Add locally and sync backend
        selectionApi.addSelections(sessionId, [question.id]).catch(console.error);
        return [...prev, question];
      }
    });
  };

  const selectMultiple = (questionsList) => {
    setSelectedQuestions((prev) => {
      const currentIds = new Set(prev.map((q) => q.id));
      const newItems = questionsList.filter((q) => !currentIds.has(q.id));
      if (newItems.length > 0) {
        selectionApi.addSelections(sessionId, newItems.map((q) => q.id)).catch(console.error);
      }
      return [...prev, ...newItems];
    });
  };

  const deselectMultiple = (questionIds) => {
    const idSet = new Set(questionIds);
    setSelectedQuestions((prev) => {
      idSet.forEach((id) => {
        selectionApi.removeSelection(sessionId, id).catch(console.error);
      });
      return prev.filter((q) => !idSet.has(q.id));
    });
  };

  const removeQuestion = (questionId) => {
    setSelectedQuestions((prev) => prev.filter((q) => q.id !== questionId));
    selectionApi.removeSelection(sessionId, questionId).catch(console.error);
  };

  const clearAll = () => {
    setSelectedQuestions([]);
    selectionApi.clearSelections(sessionId).catch(console.error);
  };

  // Compute distributions
  const subjectDistribution = {};
  const chapterDistribution = {};
  selectedQuestions.forEach((q) => {
    const s = q.subject || 'OTHER';
    subjectDistribution[s] = (subjectDistribution[s] || 0) + 1;
    const c = q.chapter || 'General';
    chapterDistribution[c] = (chapterDistribution[c] || 0) + 1;
  });

  return (
    <SelectionContext.Provider
      value={{
        selectedQuestions,
        selectedCount: selectedQuestions.length,
        isSelected,
        toggleQuestion,
        selectMultiple,
        deselectMultiple,
        removeQuestion,
        clearAll,
        subjectDistribution,
        chapterDistribution,
      }}
    >
      {children}
    </SelectionContext.Provider>
  );
}

export function useSelection() {
  const context = useContext(SelectionContext);
  if (!context) {
    throw new Error('useSelection must be used within SelectionProvider');
  }
  return context;
}

