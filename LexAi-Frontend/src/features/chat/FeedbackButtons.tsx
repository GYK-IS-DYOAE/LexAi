import { ThumbsUp, ThumbsDown } from "lucide-react";

export type Vote = "like" | "dislike" | null;

interface FeedbackButtonsProps {
  vote?: Vote;
  onVote: (vote: Exclude<Vote, null>) => void;
}

export default function FeedbackButtons({ vote, onVote }: FeedbackButtonsProps) {
  return (
    <div className="flex items-center gap-3 mt-2">
      <button
        onClick={() => onVote("like")}
        className={`transition-colors duration-150 focus:outline-none ${
          vote === "like"
            ? "text-green-500"
            : "text-[hsl(var(--muted-foreground))] hover:text-green-400"
        }`}
        title="Beğendim"
      >
        <ThumbsUp size={18} strokeWidth={2} />
      </button>

      <button
        onClick={() => onVote("dislike")}
        className={`transition-colors duration-150 focus:outline-none ${
          vote === "dislike"
            ? "text-red-500"
            : "text-[hsl(var(--muted-foreground))] hover:text-red-400"
        }`}
        title="Beğenmedim"
      >
        <ThumbsDown size={18} strokeWidth={2} />
      </button>
    </div>
  );
}
