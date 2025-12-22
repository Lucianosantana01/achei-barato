export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.1"
  }
  public: {
    Tables: {
      notification_logs: {
        Row: {
          alert_id: string | null
          channel: Database["public"]["Enums"]["notification_channel"]
          created_at: string
          error_message: string | null
          id: string
          payload: Json | null
          status: Database["public"]["Enums"]["notification_status"]
          user_id: string
        }
        Insert: {
          alert_id?: string | null
          channel: Database["public"]["Enums"]["notification_channel"]
          created_at?: string
          error_message?: string | null
          id?: string
          payload?: Json | null
          status?: Database["public"]["Enums"]["notification_status"]
          user_id: string
        }
        Update: {
          alert_id?: string | null
          channel?: Database["public"]["Enums"]["notification_channel"]
          created_at?: string
          error_message?: string | null
          id?: string
          payload?: Json | null
          status?: Database["public"]["Enums"]["notification_status"]
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "notification_logs_alert_id_fkey"
            columns: ["alert_id"]
            isOneToOne: false
            referencedRelation: "price_alerts"
            referencedColumns: ["id"]
          },
        ]
      }
      offers: {
        Row: {
          brand: string | null
          category: string | null
          condition: Database["public"]["Enums"]["product_condition"]
          created_at: string
          currency: string
          description: string | null
          external_id: string | null
          id: string
          image_url: string | null
          in_stock: boolean | null
          original_price: number | null
          price: number
          purchase_url: string
          rating: number | null
          rating_count: number | null
          shipping_cost: number | null
          shipping_info: string | null
          source_id: string | null
          store_name: string
          title: string
          updated_at: string
        }
        Insert: {
          brand?: string | null
          category?: string | null
          condition?: Database["public"]["Enums"]["product_condition"]
          created_at?: string
          currency?: string
          description?: string | null
          external_id?: string | null
          id?: string
          image_url?: string | null
          in_stock?: boolean | null
          original_price?: number | null
          price: number
          purchase_url: string
          rating?: number | null
          rating_count?: number | null
          shipping_cost?: number | null
          shipping_info?: string | null
          source_id?: string | null
          store_name: string
          title: string
          updated_at?: string
        }
        Update: {
          brand?: string | null
          category?: string | null
          condition?: Database["public"]["Enums"]["product_condition"]
          created_at?: string
          currency?: string
          description?: string | null
          external_id?: string | null
          id?: string
          image_url?: string | null
          in_stock?: boolean | null
          original_price?: number | null
          price?: number
          purchase_url?: string
          rating?: number | null
          rating_count?: number | null
          shipping_cost?: number | null
          shipping_info?: string | null
          source_id?: string | null
          store_name?: string
          title?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "offers_source_id_fkey"
            columns: ["source_id"]
            isOneToOne: false
            referencedRelation: "store_sources"
            referencedColumns: ["id"]
          },
        ]
      }
      price_alerts: {
        Row: {
          active: boolean
          created_at: string
          id: string
          last_triggered_at: string | null
          percentage_drop: number | null
          stores: string[] | null
          target_price: number
          term: string
          updated_at: string
          user_id: string
        }
        Insert: {
          active?: boolean
          created_at?: string
          id?: string
          last_triggered_at?: string | null
          percentage_drop?: number | null
          stores?: string[] | null
          target_price: number
          term: string
          updated_at?: string
          user_id: string
        }
        Update: {
          active?: boolean
          created_at?: string
          id?: string
          last_triggered_at?: string | null
          percentage_drop?: number | null
          stores?: string[] | null
          target_price?: number
          term?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      profiles: {
        Row: {
          created_at: string
          credit_reset_at: string
          credits_remaining: number
          id: string
          name: string | null
          phone_whatsapp: string | null
          plan: Database["public"]["Enums"]["user_plan"]
          pro_cycle_end: string | null
          pro_cycle_start: string | null
          updated_at: string
        }
        Insert: {
          created_at?: string
          credit_reset_at?: string
          credits_remaining?: number
          id: string
          name?: string | null
          phone_whatsapp?: string | null
          plan?: Database["public"]["Enums"]["user_plan"]
          pro_cycle_end?: string | null
          pro_cycle_start?: string | null
          updated_at?: string
        }
        Update: {
          created_at?: string
          credit_reset_at?: string
          credits_remaining?: number
          id?: string
          name?: string | null
          phone_whatsapp?: string | null
          plan?: Database["public"]["Enums"]["user_plan"]
          pro_cycle_end?: string | null
          pro_cycle_start?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      search_queries: {
        Row: {
          created_at: string
          credits_consumed: number
          filters: Json | null
          id: string
          results_count: number | null
          term: string
          user_id: string | null
        }
        Insert: {
          created_at?: string
          credits_consumed?: number
          filters?: Json | null
          id?: string
          results_count?: number | null
          term: string
          user_id?: string | null
        }
        Update: {
          created_at?: string
          credits_consumed?: number
          filters?: Json | null
          id?: string
          results_count?: number | null
          term?: string
          user_id?: string | null
        }
        Relationships: []
      }
      store_sources: {
        Row: {
          active: boolean
          config: Json | null
          created_at: string
          id: string
          logo_url: string | null
          name: string
          type: Database["public"]["Enums"]["source_type"]
          updated_at: string
        }
        Insert: {
          active?: boolean
          config?: Json | null
          created_at?: string
          id?: string
          logo_url?: string | null
          name: string
          type?: Database["public"]["Enums"]["source_type"]
          updated_at?: string
        }
        Update: {
          active?: boolean
          config?: Json | null
          created_at?: string
          id?: string
          logo_url?: string | null
          name?: string
          type?: Database["public"]["Enums"]["source_type"]
          updated_at?: string
        }
        Relationships: []
      }
      system_settings: {
        Row: {
          description: string | null
          id: string
          key: string
          updated_at: string
          value: Json
        }
        Insert: {
          description?: string | null
          id?: string
          key: string
          updated_at?: string
          value: Json
        }
        Update: {
          description?: string | null
          id?: string
          key?: string
          updated_at?: string
          value?: Json
        }
        Relationships: []
      }
      user_roles: {
        Row: {
          created_at: string
          id: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Insert: {
          created_at?: string
          id?: string
          role?: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Update: {
          created_at?: string
          id?: string
          role?: Database["public"]["Enums"]["app_role"]
          user_id?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      has_role: {
        Args: {
          _role: Database["public"]["Enums"]["app_role"]
          _user_id: string
        }
        Returns: boolean
      }
    }
    Enums: {
      app_role: "admin" | "user"
      notification_channel: "WHATSAPP" | "EMAIL"
      notification_status: "PENDING" | "SENT" | "FAILED"
      product_condition: "new" | "used" | "refurbished"
      source_type: "API" | "FEED" | "MOCK"
      user_plan: "FREE" | "PRO"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      app_role: ["admin", "user"],
      notification_channel: ["WHATSAPP", "EMAIL"],
      notification_status: ["PENDING", "SENT", "FAILED"],
      product_condition: ["new", "used", "refurbished"],
      source_type: ["API", "FEED", "MOCK"],
      user_plan: ["FREE", "PRO"],
    },
  },
} as const
