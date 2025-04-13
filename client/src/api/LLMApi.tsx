import { useMutation } from "@tanstack/react-query";

const API_BASE_URL = import.meta.env.VITE_BASE_URL;

type TravelQuestion = {
  query: string;
};

type TravelResponse = {
  status: string;
  answer: string;
  model: string;
};

export const useAskTravelQuestion = () => {
  const askTravelQuestionRequest = async (question: TravelQuestion): Promise<TravelResponse> => {
    const response = await fetch(`${API_BASE_URL}/api/llm/ask-question`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(question),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.detail || "Failed to get answer from Travel AI";
      throw new Error(errorMessage);
    }
    
    return response.json();
  };
  
  const {
    mutateAsync: askQuestion,
    isPending,
    isError,
    isSuccess,
    data: travelResponse,
    reset
  } = useMutation({
    mutationFn: askTravelQuestionRequest
  });
  
  return {
    askQuestion,
    isLoading: isPending,
    isError,
    isSuccess,
    travelResponse,
    reset
  };
};